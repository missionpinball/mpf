"""RPC Interface for BCP clients."""
import copy
import logging

from mpf.core.bcp.bcp_socket_client import encode_command_string, BCPClientSocket
from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.player import Player
from mpf.core.utility_functions import Util


class BcpInterface(object):

    """The parent class for the BCP client.

    This class can support connections with multiple remote hosts at the same
    time using multiple instances of the BCPClientSocket class.

    Args:
        machine: A reference to the main MPF machine object.

    The following BCP commands are currently implemented:
        config?volume=0.5
        error
        get
        goodbye
        hello?version=xxx&controller_name=xxx&controller_version=xxx
        mode_start?name=xxx&priority=xxx
        mode_stop?name=xxx
        player_added?player_num=x
        player_score?value=x&prev_value=x&change=x&player_num=x
        player_turn_start?player_num=x
        player_variable?name=x&value=x&prev_value=x&change=x&player_num=x
        set
        shot?name=x
        switch?name=x&state=x
        timer
        trigger?name=xxx

    """

    def __init__(self, machine):
        """Initialise BCP."""
        self.log = logging.getLogger('BCP')
        self.machine = machine

        if 'bcp' not in machine.config or not machine.config['bcp']:
            self.configured = False
            return

        self.configured = True

        self.config = machine.config['bcp']
        self.bcp_events = dict()
        self.bcp_clients = list()
        self.active_connections = 0

        self.bcp_receive_commands = dict(
            error=self.bcp_receive_error,
            switch=self.bcp_receive_switch,
            trigger=self.bcp_receive_trigger,
            register_trigger=self.bcp_receive_register_trigger,
            get=self.bcp_receive_get,
            set=self.bcp_receive_set,
            reset_complete=self.bcp_receive_reset_complete,
            dmd_frame=self.bcp_receive_dmd_frame,
            rgb_dmd_frame=self.bcp_receive_rgb_dmd_frame)

        self.physical_dmd_update_callback = None
        self.physical_rgb_dmd_update_callback = None
        self.filter_player_events = True
        self.filter_machine_vars = True
        self.send_player_vars = False
        self.send_machine_vars = False
        self.track_volumes = dict()
        self.volume_control_enabled = False

        self.connection_callbacks = list()

        self.registered_trigger_events = CaseInsensitiveDict()

        # Add the following to the set of events that already have mpf mc
        # triggers since these are all posted on the mc side already
        self.add_registered_trigger_event('ball_started')
        self.add_registered_trigger_event('ball_ended')
        self.add_registered_trigger_event('player_add_success')

        try:
            self.bcp_events = self.config['event_map']
            self.process_bcp_events()
        except KeyError:
            pass

        self._parse_filters_from_config()

        self._setup_machine_var_monitor()

        self.machine.events.add_handler('init_phase_1',
                                        self._setup_dmds)

        self.machine.events.add_handler('player_add_success',
                                        self.bcp_player_added)
        self.machine.events.add_handler('machine_reset_phase_1',
                                        self.bcp_reset)

        self.machine.mode_controller.register_start_method(
            self.bcp_mode_start, 'mode')

    def __repr__(self):
        return '<BCP Module>'

    def register_command_callback(self, cmd, callback):
        pass

    def unregister_command_callback(self, cmd, callback):
        pass

    def _register_connection_callback(self, callback):
        # This is a callback that is called after BCP is connected. If
        # bcp is connected when this is called, the callback will be called
        # at the end of the current frame.
        if callable(callback):
            self.connection_callbacks.append(callback)

            if self.active_connections:
                self.machine.clock.schedule_once(callback, -1)

    def add_registered_trigger_event(self, event):
        if not self.configured:
            return
        try:
            self.registered_trigger_events[event] += 1
        except KeyError:
            self.registered_trigger_events[event] = 1
            self.machine.events.add_handler(event=event,
                                            handler=self.bcp_trigger,
                                            name=event)

    def remove_registered_trigger_event(self, event):
        if not self.configured:
            return
        try:
            self.registered_trigger_events[event] -= 1
            if not self.registered_trigger_events[event]:
                del self.registered_trigger_events[event]
                self.machine.events.remove_handler_by_event(
                    event=event, handler=self.bcp_trigger)
        except KeyError:
            pass

    def _setup_dmds(self):
        if 'physical_dmd' in self.machine.config:
            self._setup_dmd()

        if 'physical_rgb_dmd' in self.machine.config:
            self._setup_rgb_dmd()

    def _setup_dmd(self):
        if self.machine.config['hardware']['dmd'] == 'default':
            platform = self.machine.default_platform
        else:
            try:
                platform = self.machine.hardware_platforms[
                    self.machine.config['hardware']['dmd']]
            except KeyError:
                return

        if platform.features['has_dmd']:
            self._register_connection_callback(platform.configure_dmd)

    def _setup_rgb_dmd(self):
        if self.machine.config['hardware']['rgb_dmd'] == 'default':
            platform = self.machine.default_platform
        else:
            try:
                platform = self.machine.hardware_platforms[
                    self.machine.config['hardware']['rgb_dmd']]
            except KeyError:
                return

        if platform.features['has_rgb_dmd']:
            # print("RGB DMD PLATFORM ", platform)
            self._register_connection_callback(platform.configure_rgb_dmd)

    def register_dmd(self, dmd_update_meth):
        self.physical_dmd_update_callback = dmd_update_meth
        self.send('dmd_start')

    def register_rgb_dmd(self, dmd_update_meth):
        self.physical_rgb_dmd_update_callback = dmd_update_meth
        self.send('rgb_dmd_start')

    def _parse_filters_from_config(self):
        if ('player_variables' in self.config and
                self.config['player_variables']):

            self.send_player_vars = True

            self.config['player_variables'] = (
                Util.string_to_list(self.config['player_variables']))

            if '__all__' in self.config['player_variables']:
                self.filter_player_events = False

        self._setup_player_monitor()

        if ('machine_variables' in self.config and
                self.config['machine_variables']):

            self.send_machine_vars = True

            self.config['machine_variables'] = (
                Util.string_to_list(self.config['machine_variables']))

            if '__all__' in self.config['machine_variables']:
                self.filter_machine_vars = False

    def _send_machine_vars(self):
        for var_name, settings in self.machine.machine_vars.items():

            self.send(bcp_command='machine_variable',
                      name=var_name,
                      value=settings['value'])

    def remove_bcp_connection(self, bcp_client):
        """Remove a BCP connection to a remote BCP host.

        Args:
            bcp_client: A reference to the BCPClientSocket instance you want to
                remove.
        """
        try:
            self.bcp_clients.remove(bcp_client)
        except ValueError:
            pass

    def _setup_player_monitor(self):
        Player.monitor_enabled = True
        self.machine.register_monitor('player', self._player_var_change)

        # Since we have a player monitor setup, we need to add whatever events
        # it will send to our ignored list. Otherwise
        # register_mpfmc_trigger_events() will register for them too and they'll
        # be sent twice
        self.add_registered_trigger_event('player_score')

        # figure out which player events are being sent already and add them to
        # the list so we don't send them again
        if self.filter_player_events:
            for event in self.config['player_variables']:
                self.add_registered_trigger_event('player_{}'.format(event))

    def _setup_machine_var_monitor(self):
        self.machine.machine_var_monitor = True
        self.machine.register_monitor('machine_vars', self._machine_var_change)

        if self.filter_machine_vars:
            for event in self.config['machine_variables']:
                self.add_registered_trigger_event('machine_var_{}'.format(
                    event))

    # pylint: disable-msg=too-many-arguments
    def _player_var_change(self, name, value, prev_value, change, player_num):
        if name == 'score':
            self.send('player_score', value=value, prev_value=prev_value,
                      change=change, player_num=player_num)

        elif self.send_player_vars and (
                not self.filter_player_events or
                name in self.config['player_variables']):
            self.send(bcp_command='player_variable',
                      name=name,
                      value=value,
                      prev_value=prev_value,
                      change=change,
                      player_num=player_num)

    def _machine_var_change(self, name, value, prev_value, change):
        if self.send_machine_vars and (
                not self.filter_machine_vars or
                name in self.config['machine_variables']):
            self.send(bcp_command='machine_variable',
                      name=name,
                      value=value,
                      prev_value=prev_value,
                      change=change)

    def process_bcp_events(self):
        """Process the BCP Events from the config."""
        # config is localized to BCPEvents
        for event, settings in self.bcp_events.items():
            if 'params' in settings:
                self.machine.events.add_handler(event,
                                                self._bcp_event_callback,
                                                command=settings['command'],
                                                params=settings['params'])

            else:
                self.machine.events.add_handler(event,
                                                self._bcp_event_callback,
                                                command=settings['command'])

    def _replace_variables(self, value, kwargs):
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
            for name, val in kwargs.items():
                if '%' + name in value:
                    value = value.replace('%' + name, str(val))

        return value

    def _bcp_event_callback(self, command, params=None, **kwargs):
        if params:
            params = copy.deepcopy(params)
            for param, value in params.items():
                params[param] = self._replace_variables(value, kwargs)

            self.send(command, **params)

        else:
            self.send(command)

    def send(self, bcp_command, callback=None, **kwargs):
        """Send a BCP message.

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
        if not self.configured:
            return
        bcp_string = encode_command_string(bcp_command, **kwargs)

        for client in self.bcp_clients:
            client.send(bcp_string)

        if callback:
            callback()

    def process_bcp_message(self, cmd, kwargs, rawbytes):
        """Process BCP message.

        Args:
            cmd:
            kwargs:
            rawbytes:
        """
        self.log.debug("Processing command: %s %s", cmd, kwargs)

        if cmd in self.bcp_receive_commands:
            self.bcp_receive_commands[cmd](rawbytes=rawbytes, **kwargs)
        else:
            self.log.warning("Received invalid BCP command: %s", cmd)

    def shutdown(self):
        """Prepare the BCP clients for MPF shutdown."""
        for client in self.bcp_clients:
            client.stop()

    def bcp_receive_error(self, rawbytes, **kwargs):
        """A remote BCP host has sent a BCP error message, indicating that a
        command from MPF was not recognized.

        This method only posts a warning to the log. It doesn't do anything else
        at this point.
        """
        del rawbytes
        self.log.warning('Received Error command from host with parameters: %s',
                         kwargs)

    def bcp_receive_get(self, names, rawbytes, **kwargs):
        """Process an incoming BCP 'get' command by posting an event 'bcp_get_<name>'.

        It's up to an event handler to register for that event and to send the response BCP 'set' command.
        """
        del kwargs
        del rawbytes
        for name in Util.string_to_list(names):
            self.machine.events.post('bcp_get_{}'.format(name))
        '''event: bcp_get_(name)

        desc: A BCP get command was received.
        '''

    def bcp_receive_set(self, rawbytes, **kwargs):
        """Process an incoming BCP 'set' command by posting an event
        'bcp_set_<name>' with a parameter value=<value>. It's up to an event
        handler to register for that event and to do something with it.

        Note that BCP set commands can contain multiple key/value pairs, and
        this method will post one event for each pair.

        """
        del rawbytes
        for k, v in kwargs.items():
            self.machine.events.post('bcp_set_{}'.format(k), value=v)
        '''event: bcp_set_(name)

        A BCP set command was received.

        args:

        value: The value of the "name" variable to set.
        '''

    def bcp_client_connected(self, client):
        # TODO: use client
        self._send_machine_vars()

        self.bcp_clients.append(client)

        for callback in self.machine.bcp.connection_callbacks:
            callback()

    def bcp_receive_reset_complete(self, rawbytes, **kwargs):
        del kwargs
        del rawbytes
        self.machine.bcp_reset_complete()

    def bcp_mode_start(self, config, priority, mode, **kwargs):
        """Send BCP 'mode_start' to the connected BCP hosts.

        Schedule automatic sending of 'mode_stop' when the mode stops.
        """
        del config
        del kwargs
        self.send('mode_start', name=mode.name, priority=priority)

        return self.bcp_mode_stop, mode.name

    def bcp_mode_stop(self, name, **kwargs):
        """Send BCP 'mode_stop' to the connected BCP hosts."""
        del kwargs
        self.send('mode_stop', name=name)

    def bcp_reset(self):
        """Sends the 'reset' command to the remote BCP host."""
        self.send('reset')

    def bcp_receive_switch(self, name, state, rawbytes, **kwargs):
        """Process an incoming switch state change request from a remote BCP host.

        Args:
            name: String name of the switch to set.
            state: Integer representing the state this switch will be set to.
                1 = active, 0 = inactive, -1 means this switch will be flipped
                from whatever its current state is to the opposite state.
        """
        del kwargs
        del rawbytes
        state = int(state)

        if name not in self.machine.switches:
            self.log.warning("Received BCP switch message with invalid switch"
                             "name: '%s'", name)
            return

        if state == -1:
            if self.machine.switch_controller.is_active(name):
                state = 0
            else:
                state = 1

        self.machine.switch_controller.process_switch(name=name,
                                                      state=state,
                                                      logical=True)

    def bcp_receive_dmd_frame(self, rawbytes, **kwargs):
        """Called when the BCP client receives a new DMD frame from the remote BCP host.

        This method forwards the frame to the physical DMD.
        """
        del kwargs
        self.physical_dmd_update_callback(rawbytes)

    def bcp_receive_rgb_dmd_frame(self, rawbytes, **kwargs):
        """Called when the BCP client receives a new RGB DMD frame from the remote BCP host.

        This method forwards the frame to the physical DMD.
        """
        del kwargs
        self.physical_rgb_dmd_update_callback(rawbytes)

    def bcp_receive_register_trigger(self, event, rawbytes, **kwargs):
        del rawbytes
        del kwargs
        self.add_registered_trigger_event(event)

    def bcp_player_added(self, player, num):
        """Send BCP 'player_added' to the connected BCP hosts."""
        del player
        self.send('player_added', player_num=num)

    def bcp_trigger(self, name, **kwargs):
        """Send BCP 'trigger' to the connected BCP hosts."""
        # Since player variables are sent automatically, if we get a trigger
        # for an event that starts with "player_", we need to only send it here
        # if there's *not* a player variable with that name, since if there is
        # a player variable then the player variable handler will send it.
        if name.startswith('player_'):
            try:
                if self.machine.game.player.is_player_var(name.lstrip('player_')):
                    return

            except AttributeError:
                pass

        self.send(bcp_command='trigger', name=name, **kwargs)

    def bcp_receive_trigger(self, name=None, rawbytes=None, **kwargs):
        """Process an incoming trigger command from a remote BCP host."""
        if not name:
            return

        del rawbytes

        if 'callback' in kwargs:
            self.machine.events.post(event=name,
                                     callback=self.bcp_trigger,
                                     name=kwargs.pop('callback'),
                                     **kwargs)

        else:
            self.machine.events.post(event=name, **kwargs)

