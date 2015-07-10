""" MPF plugin which enables the Backbox Control Protocol (BCP) v1.0alpha"""
# bcp.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# The Backbox Control Protocol was conceived and developed by:
# Quinn Capen
# Kevin Kelm
# Gabe Knuth
# Brian Madden
# Mike ORourke

# Documentation and more info at http://missionpinball.com/mpf

import logging
import socket
import threading
import sys
import traceback
import urllib
import urlparse
from Queue import Queue
import copy
import time

from mpf.game.player import Player
from mpf.system.config import Config
import version


def decode_command_string(bcp_string):
    """Decodes a BCP command string into separate command and paramter parts.

    Args:
        bcp_string: The incoming UTF-8, URL encoded BCP command string.

    Returns:
        A tuple of the command string and a dictionary of kwarg pairs.

    Example:
        Input: trigger?name=hello&foo=foo%20bar
        Output: ('trigger', {'name': 'hello', 'foo': 'foo bar'})

    """
    bcp_command = urlparse.urlsplit(bcp_string.lower())
    try:
        kwargs = urlparse.parse_qs(bcp_command.query)

    except AttributeError:
        kwargs = dict()

    for k, v in kwargs.iteritems():
        kwargs[k] = urllib.unquote(v[0])

    return bcp_command.path, kwargs


def encode_command_string(bcp_command, **kwargs):
    """Encodes a BCP command and kwargs into a valid BCP command string.

    Args:
        bcp_command: String of the BCP command name.
        **kwargs: Optional pair(s) of kwargs which will be appended to the
            command.

    Returns:
        A string.

    Example:
        Input: encode_command_string('trigger', {'name': 'hello', 'foo': 'bar'})
        Output: trigger?name=hello&foo=bar

    """
    kwarg_string = ''

    try:
        for k, v in kwargs.iteritems():

            kwarg_string += (urllib.quote(k.lower(), '') + '=' +
                             urllib.quote(str(v).lower(), '') + '&')

        kwarg_string = kwarg_string[:-1]

    except (TypeError, AttributeError):
        pass

    return unicode(urlparse.urlunparse((None, None, bcp_command.lower(), None,
                                        kwarg_string, None)), 'utf-8')


class BCP(object):
    """The parent class for the BCP client.

    This class can support connections with multiple remote hosts at the same
    time using multiple instances of the BCPClient class.

    Args:
        machine: A reference to the main MPF machine object.

    The following BCP commands are currently implemented:
        attract_start
        attract_stop
        ball_start?player=x&ball=x
        ball_end
        config?volume=0.5
        error
        game_start
        game_end
        get
        goodbye
        hello?version=xxx
        mode_start?name=xxx&priority=xxx
        mode_stop?name=xxx
        player_added?number=x
        player_score?value=x&prev_value=x&change=x
        player_turn_start?player=x
        player_variable?name=x&value=x&prev_value=x&change=x
        set
        switch?name=x&state=x
        timer
        trigger?name=xxx

    """

    def __init__(self, machine):
        if ('bcp' not in machine.config or
                'connections' not in machine.config['bcp']):
            return

        self.log = logging.getLogger('BCP')
        self.machine = machine

        self.config = machine.config['bcp']
        self.receive_queue = Queue()
        self.bcp_events = dict()
        self.connection_config = self.config['connections']
        self.bcp_clients = list()

        self.bcp_receive_commands = {'error': self.bcp_receive_error,
                                     'switch': self.bcp_receive_switch,
                                     'trigger': self.bcp_receive_trigger,
                                     'get': self.bcp_receive_get,
                                     'set': self.bcp_receive_set
                                    }

        self.dmd = None

        self.filter_player_events = True
        self.send_player_vars = False
        self.mpfmc_trigger_events = set()
        self.track_volumes = dict()
        self.volume_control_enabled = False

        # Add the following to the set of events that already have mpf mc
        # triggers since these are all posted on the mc side already
        self.mpfmc_trigger_events.add('timer_tick')
        self.mpfmc_trigger_events.add('ball_started')
        self.mpfmc_trigger_events.add('ball_ended')
        self.mpfmc_trigger_events.add('game_starting')
        self.mpfmc_trigger_events.add('game_ended')
        self.mpfmc_trigger_events.add('player_add_success')
        self.mpfmc_trigger_events.add('machineflow_Attract_start')
        self.mpfmc_trigger_events.add('machineflow_Attract_stop')

        try:
            if self.machine.config['dmd']['physical']:
                self._setup_dmd()
        except KeyError:
            pass

        try:
            self.bcp_events = self.config['event_map']
            self.process_bcp_events()
        except KeyError:
            pass

        try:
            self._setup_track_volumes(self.machine.config['volume'])
        except KeyError:
            self.log.warning("No 'Volume:' section in config file")

        if ('player_variables' in self.config and
                self.config['player_variables']):

            self.send_player_vars = True

            self.config['player_variables'] = (
                Config.string_to_list(self.config['player_variables']))

            if '__all__' in self.config['player_variables']:
                self.filter_player_events = False

        self._setup_player_monitor()
        self.register_mpfmc_trigger_events(self.machine.config)

        try:
            self.register_triggers(self.machine.config['triggers'])
        except KeyError:
            pass

        self.machine.events.add_handler('init_phase_2',
                                        self._setup_bcp_connections)
        self.machine.events.add_handler('timer_tick', self.get_bcp_messages)
        self.machine.events.add_handler('game_starting', self.bcp_game_start)
        self.machine.events.add_handler('player_add_success',
                                        self.bcp_player_added)
        self.machine.events.add_handler('machine_reset_phase_1',
                                        self.bcp_reset)
        self.machine.events.add_handler('increase_volume', self.increase_volume)
        self.machine.events.add_handler('decrease_volume', self.decrease_volume)
        self.machine.events.add_handler('enable_volume_keys',
                                        self.enable_volume_keys)
        self.machine.events.add_handler('disable_volume_keys',
                                        self.disable_volume_keys)

        self.machine.modes.register_start_method(self.bcp_mode_start, 'mode')
        self.machine.modes.register_start_method(self.register_triggers,
                                                 'triggers')
        self.machine.modes.register_load_method(
            self.register_mpfmc_trigger_events)

    def _setup_dmd(self):

        dmd_platform = self.machine.default_platform

        if self.machine.physical_hw:

            if self.machine.config['hardware']['dmd'] != 'default':
                dmd_platform = (self.machine.hardware_platforms
                                [self.machine.config['platform']['dmd']])

        self.dmd = dmd_platform.configure_dmd()

    def _setup_bcp_connections(self):
        for name, settings in self.connection_config.iteritems():
            if 'host' not in settings:
                break

            self.bcp_clients.append(BCPClient(self.machine, name,
                                              settings, self.receive_queue))

    def remove_bcp_connection(self, bcp_client):
        """Removes a BCP connection to a remote BCP host.

        Args:
            bcp_client: A reference to the BCPClient instance you want to
                remove.

        """
        try:
            self.bcp_clients.remove(self)
        except ValueError:
            pass

    def _setup_player_monitor(self):
        Player.monitor_enabled = True
        self.machine.register_monitor('player', self._player_var_change)

        # Since we have a player monitor setup, we need to add whatever events
        # it will send to our ignored list. Otherwise
        # register_mpfmc_trigger_events() will register for them too and they'll
        # be sent twice

        self.mpfmc_trigger_events.add('player_score')

        # figure out which player events are being sent already and add them to
        # the list so we don't send them again
        if self.filter_player_events:
            for event in self.config['player_variables']:
                self.mpfmc_trigger_events.add('player_' + event.lower())

    def _player_var_change(self, name, value, prev_value, change):

        if name == 'score':
            self.send('player_score', value=value, prev_value=prev_value,
                      change=change)

        elif self.send_player_vars and (
                not self.filter_player_events or
                name in self.config['player_variables']):
            self.send(bcp_command='player_variable',
                      name=name,
                      value=value,
                      prev_value=prev_value,
                      change=change)

    def process_bcp_events(self):
        """Processes the BCP Events from the config."""
        # config is localized to BCPEvents

        for event, settings in self.bcp_events.iteritems():

            if 'params' in settings:

                self.machine.events.add_handler(event, self._bcp_event_callback,
                                                command=settings['command'],
                                                params=settings['params'])

            else:
                self.machine.events.add_handler(event, self._bcp_event_callback,
                                                command=settings['command'])

    def _bcp_event_callback(self, command, params=None, **kwargs):
        if params:

            params = copy.deepcopy(params)

            for param, value in params.iteritems():

                # Are there any text variables to replace on the fly?
                # todo should this go here?
                if '%' in value:

                    # first check for player vars (%var_name%)
                    if self.machine.game and self.machine.game.player:
                        for name, val in self.machine.game.player:
                            if '%' + name + '%' in value:
                                value = value.replace('%' + name + '%',
                                                      str(val))

                    # now check for single % which means event kwargs
                    for name, val in kwargs.iteritems():
                        if '%' + name in value:
                            params[param] = value.replace('%' + name, str(val))

            self.send(command, **params)

        else:
            self.send(command)

    def register_mpfmc_trigger_events(self, config, **kwargs):
        """Scans an MPF config file and creates trigger events for the config
        settings that need them.

        Args:
            config: An MPF config dictionary (can be the machine-wide or a mode-
                specific one).
            **kwargs: Not used. Included to catch any additional kwargs that may
                be associted with this method being registered as an event
                handler.

        """

        self.log.debug("Registering Trigger Events")

        # todo should this be here? Or in the individual showplayer, soundplayer
        # and slideplayer modules?

        try:
            for event in config['showplayer'].keys():
                self.create_trigger_event(event)
        except KeyError:
            pass

        try:
            for event in config['slideplayer'].keys():
                self.create_trigger_event(event)
        except KeyError:
            pass

        try:
            for k, v in config['soundplayer'].iteritems():
                if 'start_events' in v:
                    for event in Config.string_to_list(v['start_events']):
                        self.create_trigger_event(event)
                if 'stop_events' in v:
                    for event in Config.string_to_list(v['stop_events']):
                        self.create_trigger_event(event)
        except KeyError:
            pass

    def create_trigger_event(self, event):
        """Registers a BCP trigger based on an MPF event.

        Args:
            event: String name of the event you're registering this trigger for.

        The BCP trigger will be registered with the same name as the MPF event.
        For example, if you pass the event "foo_event", the BCP command that
        will be sent when that event is posted will be trigger?name=foo_event.

        """

        if not self.filter_player_events and event.startswith('player_'):
            return  # since all player events are already being sent

        if event not in self.mpfmc_trigger_events:

            self.machine.events.add_handler(event, handler=self.send,
                                            bcp_command='trigger',
                                            name=event)
            self.mpfmc_trigger_events.add(event)

    def register_triggers(self, config, priority=0, mode=None):
        """Sets up trigger events based on a 'triggers:' section of a config
        dictionary.

        Args:
            config: A python config dictionary.
            priority: (not used) Included since this method is called as part of
                a mode start which passed this parameter.
            mode: (not used) Included since this method is called as part of
                a mode start which passed this parameter.

        """
        # config is localized to 'Trigger'

        event_list = list()

        for event, settings in config.iteritems():

            params = dict()

            try:
                params = copy.deepcopy(settings['params'])
            except KeyError:
                pass

            try:
                event_list.append(self.machine.events.add_handler(
                    event, handler=self.send, bcp_command='trigger',
                    name=settings['bcp_name'], **params))
            except KeyError:
                self.log.warning("Could not create trigger event for '%s'. "
                                 "Settings: %s",
                                 event, settings)

        return self.machine.events.remove_handlers_by_keys, event_list

    def send(self, bcp_command, callback=None, **kwargs):
        """Sends a BCP message.

        Args:
            bcp_command: String name of the BCP command that will be sent.
            callback: An optional callback method that will be called as soon as
                the BCP command is sent.
            **kwargs: Optional kwarg pairs that will be sent as parameters along
                with the BCP command.

        Example:
            If you call this method like this:
                send('trigger', ball=1, string'hello')

            The BCP command that will be sent will be this:
                trigger?ball=1&string=hello

        """

        bcp_string = encode_command_string(bcp_command, **kwargs)

        for client in self.bcp_clients:
            client.send(bcp_string)

        if callback:
            callback()

    def get_bcp_messages(self):
        """Retrieves and processes new BCP messages from the receiving queue.

        """
        while not self.receive_queue.empty():
            cmd, kwargs = self.receive_queue.get(False)

            self.log.debug("Processing command: %s %s", cmd, kwargs)

            # todo convert to try. Haven't done it yet though because I couldn't
            # figure out how to make it not swallow exceptions and it was
            # getting annoying to troubleshoot
            if cmd in self.bcp_receive_commands:
                self.bcp_receive_commands[cmd](**kwargs)
            else:
                self.log.warning("Received invalid BCP command: %s", cmd)
                self.send('error', message='invalid command',
                          command=cmd)

    def shutdown(self):
        """Prepares the BCP clients for MPF shutdown."""
        for client in self.bcp_clients:
            client.stop()

    def bcp_receive_error(self, **kwargs):
        """A remote BCP host has sent a BCP error message, indicating that a
        command from MPF was not recognized.

        This method only posts a warning to the log. It doesn't do anything else
        at this point.

        """

        self.log.warning('Received Error command from host with parameters: %s',
                         kwargs)

    def bcp_receive_get(self, **kwargs):
        """Processes an incoming BCP 'get' command.

        Note that this media controller doesn't implement the 'get' command at
        this time, but it's included here for completeness since the 'get'
        command is part of the BCP 1.0 specification so we don't want to return
        an error if we receive an incoming 'get' command.

        """
        pass

    def bcp_receive_set(self, **kwargs):
        """Processes an incoming BCP 'set' command.

        Note that this media controller doesn't implement the 'set' command at
        this time, but it's included here for completeness since the 'set'
        command is part of the BCP 1.0 specification so we don't want to return
        an error if we receive an incoming 'set' command.

        """
        pass

    def bcp_mode_start(self, config, priority, mode, **kwargs):
        """Sends BCP 'mode_start' to the connected BCP hosts and schedules
        automatic sending of 'mode_stop' when the mode stops.
        """
        self.send('mode_start', name=mode.name, priority=priority)

        return self.bcp_mode_stop, mode.name

    def bcp_mode_stop(self, name, **kwargs):
        """Sends BCP 'mode_stop' to the connected BCP hosts."""
        self.send('mode_stop', name=name)

    def bcp_reset(self):
        """Sends the 'reset' command to the remote BCP host."""
        self.send('reset')

    def bcp_receive_switch(self, **kwargs):
        """Processes an incoming switch state change request from a remote BCP
        host.
        """
        self.machine.switch_controller.process_switch(name=kwargs['name'],
                                                      state=int(kwargs['state']),
                                                      logical=True)

    def bcp_receive_dmd_frame(self, data):
        """Called when the BCP client receives a new DMD frame from the remote
        BCP host. This method forwards the frame to the physical DMD.
        """
        self.dmd.update(data)

    def bcp_game_start(self, **kwargs):
        """Sends the BCP 'game_start' and 'player_added?number=1' commands to
        the remote BCP hosts.
        """
        self.send('game_start')
        #self.send('player_added', number=1)

    def bcp_player_added(self, player, num):
        """Sends BCP 'player_added' to the connected BCP hosts."""
        self.send('player_added', number=num)

    def bcp_trigger(self, name, **kwargs):
        """Sends BCP 'trigger' to the connected BCP hosts."""
        self.send('trigger', name=name, **kwargs)

    def bcp_receive_trigger(self, name=None, **kwargs):
        """Processes an incoming trigger command from a remote BCP host.
        """
        if not name:
            return

        if 'callback' in kwargs:
            self.machine.events.post(event=name,
                                     callback=self.bcp_trigger,
                                     name=kwargs.pop('callback'),
                                     **kwargs)

        else:
            self.machine.events.post(event=name, **kwargs)

    def enable_bcp_switch(self, name):
        """Enables sending BCP switch commands when this switch changes state.

        Args:
            name: string name of the switch

        """
        self.machine.switch_controller.add_switch_handler(switch_name=name,
            callback=self._switch_sender_callback, state=1, return_info=True)
        self.machine.switch_controller.add_switch_handler(switch_name=name,
            callback=self._switch_sender_callback, state=0, return_info=True)

    def enable_bcp_switches(self, tag):
        """Enables sending BCP switch commands when a switch with a certain tag
        changes state.

        Args:
            tag: string name of the tag for the switches you want to start
                sending

        """
        for switch in self.machine.switches.items_tagged(tag):
            self.enable_bcp_switch(switch)

    def disable_bcp_switch(self, name):
        """Disables sending BCP switch commands when this switch changes state.

        Args:
            name: string name of the switch

        """
        self.machine.switch_controller.remove_switch_handler(switch_name=name,
            callback=self._switch_sender_callback, state=1)
        self.machine.switch_controller.remove_switch_handler(switch_name=name,
            callback=self._switch_sender_callback, state=0)

    def disable_bcp_switches(self, tag):
        """Disables sending BCP switch commands when a switch with a certain tag
        changes state.

        Args:
            tag: string name of the tag for the switches you want to stop
                sending
        """
        for switch in self.machine.switches.items_tagged(tag):
            self.disable_bcp_switch(switch)

    def _switch_sender_callback(self, switch_name, state, ms):
        self.send('switch', name=switch_name, state=state)

    def _setup_track_volumes(self, config):
        # config is localized to 'Volume'
        for k, v in config['tracks'].iteritems():
            self.track_volumes[k] = v

    def increase_volume(self, track='master', **kwargs):
        """Sends a command to the remote BCP host to increase the volume of a
        track by 1 unit.

        Args:
            track: The string name of the track you want to increase the volume
                on. Default is 'master'.
            **kwargs: Ignored. Included in case this method is used as a
                callback for an event which has other kwargs.

        The max value of the volume for a track is set in the Volume: Steps:
        entry in the config file. If this increase causes the volume to go above
        the max value, the increase is ignored.

        """

        try:
            self.track_volumes[track] += 1
            self.set_volume(self.track_volumes[track], track)
        except KeyError:
            self.log.warning('Received volume increase request for unknown '
                             'track "%s"', track)

    def decrease_volume(self, track='master', **kwargs):
        """Sends a command to the remote BCP host to decrease the volume of a
        track by 1 unit.

        Args:
            track: The string name of the track you want to decrease the volume
                on. Default is 'master'.
            **kwargs: Ignored. Included in case this method is used as a
                callback for an event which has other kwargs.

        If this decrease causes the volume to go below zero, the decrease is
        ignored.

        """

        try:
            self.track_volumes[track] -= 1
            self.set_volume(self.track_volumes[track], track)
        except KeyError:
            self.log.warning('Received volume decrease request for unknown '
                             'track "%s"', track)

    def enable_volume_keys(self, up_tag='volume_up', down_tag='volume_down'):
        """Enables switch handlers to change the master system volume based on
        switch tags.

        Args:
            up_tag: String of a switch tag name that will be used to set which
                switch(es), when activated, increase the volume.
            down_tag: String of a switch tag name that will be used to set which
                switch(es), when activated, decrease the volume.

        """

        if self.volume_control_enabled:
            return

        for switch in self.machine.switches.items_tagged(up_tag):
            self.machine.switch_controller.add_switch_handler(switch.name,
                self.increase_volume)

        for switch in self.machine.switches.items_tagged(down_tag):
            self.machine.switch_controller.add_switch_handler(switch.name,
                self.decrease_volume)

        self.volume_control_enabled = True

    def disable_volume_keys(self, up_tag='volume_up', down_tag='volume_down'):
        """Disables switch handlers so that the switches no longer affect the
        master system volume.

        Args:
            up_tag: String of a switch tag name of the switches that will no
                longer be used to increase the volume.
            down_tag: String of a switch tag name of the switches that will no
                longer be used to decrease the volume.

        """
        for switch in self.machine.switches.items_tagged(up_tag):
            self.machine.switch_controller.remove_switch_handler(switch.name,
                self.increase_volume)

        for switch in self.machine.switches.items_tagged(down_tag):
            self.machine.switch_controller.remove_switch_handler(switch.name,
                self.decrease_volume)

        self.volume_control_enabled = False

    def set_volume(self, volume, track='master', **kwargs):
        """Sends a command to the remote BCP host to set the volume of a track
        to the value specified.

        Args:
            volume: Int of the volume level. Valid range is 0 to the "steps"
                configuration in your config file. Values outside this range are
                ignored.
            track: The string name of the track you want to set the volume on.
                Default is 'master'.
            **kwargs: Ignored. Included in case this method is used as a
                callback for an event which has other kwargs.

        """

        try:
            volume = int(volume)
        except ValueError:
            self.log.warning("Received invalid volume setting: '%s'", volume)
            return

        try:
            if volume > self.machine.config['volume']['steps']:
                volume = self.machine.config['volume']['steps']
            elif volume < 0:
                volume = 0

            self.track_volumes[track] = volume
            volume_float = round(volume/float(self.machine.config['volume']
                                              ['steps']), 2)
            kwargs = {'volume_' + track: volume_float}
            self.send('config', **kwargs)
        except KeyError:
            self.log.warning('Received volume for unknown track "%s"', track)


class BCPClient(object):
    """Parent class for a BCP client socket. (There can be multiple of these to
    connect to multiple BCP media controllers simultaneously.)

    Args:
        machine: The main MachineController object.
        name: String name this client.
        config: A dictionary containing the configuration for this client.
        receive_queue: The shared Queue() object that holds incoming BCP
            messages.

    """

    def __init__(self, machine, name, config, receive_queue):

        self.log = logging.getLogger('BCPClient.' + name)
        self.log.info('Setting up BCP Client...')

        self.machine = machine
        self.name = name
        self.receive_queue = receive_queue

        config_spec = '''
                        host: string
                        port: int|5050
                        connection_attempts: int|-1
                        require_connection: boolean|False
                        '''

        self.config = Config.process_config(config_spec, config)

        self.sending_queue = Queue()
        self.receive_thread = None
        self.sending_thread = None
        self.socket = None
        self.connection_attempts = 0
        self.attempt_socket_connection = True
        self.send_goodbye = True

        self.bcp_commands = {'hello': self.receive_hello,
                             'goodbye': self.receive_goodbye,
                            }

        self.setup_client_socket()

    def setup_client_socket(self):
        """Sets up the client socket."""

        self.connection_attempts += 1
        if (self.config['connection_attempts'] == -1 or
                self.connection_attempts < self.config['connection_attempts']):

            self.log.debug("Attempting socket connection. Attempt: %s, Max: %s",
                           self.connection_attempts,
                           self.config['connection_attempts'])

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                self.socket.connect((self.config['host'], self.config['port']))
                self.log.info("Connected to remote BCP host %s:%s",
                              self.config['host'], self.config['port'])
                self.connection_attempts = 0

            except socket.error, v:
                self.socket = None
                self.log.warning("Failed to connect to remote BCP host %s:%s. "
                                 "Error: %s", self.config['host'],
                                 self.config['port'], v)
                if self.config['require_connection']:
                    self.log.critical("BCP connection 'require_connection' "
                                      "setting is True. Unable to continue.")
                    self.machine.done = True

            if self.create_socket_threads():
                self.send_hello()

        else:
            self.attempt_socket_connection = False
            self.log.debug("Max socket connection attempts reached. Giving up")

    def create_socket_threads(self):
        """Creates and starts the sending and receiving threads for the BCP
        socket.

        Returns:
            True if the socket exists and the threads were started. False if
            not.
        """

        if self.socket:

            self.receive_thread = threading.Thread(target=self.receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            self.sending_thread = threading.Thread(target=self.sending_loop)
            self.sending_thread.daemon = True
            self.sending_thread.start()

            return True

        else:
            return False

    def stop(self):
        """Stops and shuts down the socket client."""
        self.log.info("Stopping socket client")

        if self.socket:
            if self.send_goodbye:
                self.send('goodbye')

            self.socket.close()
            self.socket = None  # Socket threads will exit on this

    def send(self, message):
        """Sends a message to the BCP host.

        Args:
            message: String of the message to send.

        """

        if not self.socket and self.attempt_socket_connection:
            self.setup_client_socket()

        self.sending_queue.put(message)

    def receive_loop(self):
        """Receive loop which reads incoming data, assembles commands, and puts
        them onto the receive queue.

        This method is run as a thread.

        """

        socket_bytes = ''

        try:
            while self.socket:

                socket_bytes += self.get_from_socket()

                if socket_bytes:

                    while socket_bytes.startswith('dmd_frame'):
                        # trim the `dmd_frame?` so we have just the data
                        socket_bytes = socket_bytes[10:]

                        while len(socket_bytes) < 4096:
                            # If we don't have the full data, loop until we
                            # have it.
                            socket_bytes += self.get_from_socket()

                        # trim the first 4096 bytes for the dmd data
                        dmd_data = socket_bytes[:4096]
                        # Save the rest. This is +1 over the last step since we
                        # need to skip the \n separator
                        socket_bytes = socket_bytes[4097:]
                        self.machine.bcp.dmd.update(dmd_data)

                    if '\n' in socket_bytes:
                        message, socket_bytes = socket_bytes.split('\n', 1)

                        self.log.debug('Received "%s"', message)
                        cmd, kwargs = decode_command_string(message)

                        if cmd in self.bcp_commands:
                            self.bcp_commands[cmd](**kwargs)
                        else:
                            self.receive_queue.put((cmd, kwargs))

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.machine.crash_queue.put(msg)

    def get_from_socket(self, num_bytes=8192):
        """Reads and returns whatever data is sitting in the receiving socket.

        Args:
            num_bytes: Int of the max number of bytes to read.

        Returns:
            The data in raw string format.

        """
        try:
            socket_bytes = self.socket.recv(num_bytes)
        except:
            self.socket = None
            socket_bytes = None

        return socket_bytes

    def sending_loop(self):
        """Sending loop which transmits data from the sending queue to the
        remote socket.

        This method is run as a thread.
        """
        try:
            while self.socket:
                message = self.sending_queue.get()

                try:
                    self.log.debug('Sending "%s"', message)
                    self.socket.sendall(message + '\n')

                except (IOError, AttributeError):
                    # MPF is probably in the process of shutting down
                    pass

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.machine.crash_queue.put(msg)

    def receive_hello(self, **kwargs):
        """Processes incoming BCP 'hello' command."""
        self.log.debug('Received BCP Hello from host with kwargs: %s', kwargs)

    def receive_goodbye(self):
        """Processes incoming BCP 'goodbye' command."""
        self.send_goodbye = False
        self.stop()
        self.machine.bcp.remove_bcp_connection(self)

        if self.config['require_connection']:
            self.machine.bcp.shutdown()
            self.machine.done = True

    def send_hello(self):
        """Sends BCP 'hello' command."""
        self.send('hello?version=' + version.__bcp_version__)

    def send_goodbye(self):
        """Sends BCP 'goodbye' command."""
        self.send('goodbye')


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
