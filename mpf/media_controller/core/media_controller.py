"""Pygame-based media controller for MPF (BCP) v1.0"""
# media_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import sys
import time
from distutils.version import LooseVersion
import Queue


import pygame

from mpf.media_controller.core import *
from mpf.media_controller.core.bcp_server import BCPServer
from mpf.system.config import Config, CaseInsensitiveDict
from mpf.system.events import EventManager
from mpf.system.timing import Timing
from mpf.system.tasks import Task, DelayManager
from mpf.system.player import Player
from mpf.system.assets import AssetManager
import mpf.system.bcp as bcp
import version


class MediaController(object):

    def __init__(self, options):
        self.options = options

        self.log = logging.getLogger("MediaController")
        self.log.info("Media Controller Version %s", version.__version__)
        self.log.debug("Backbox Control Protocol Version %s",
                      version.__bcp_version__)
        self.log.debug("Config File Version %s",
                      version.__config_version__)

        python_version = sys.version_info

        if python_version[0] != 2 or python_version[1] != 7:
            self.log.error("Incorrect Python version. MPF requires Python 2.7."
                           "x. You have Python %s.%s.%s.", python_version[0],
                           python_version[1], python_version[2])
            sys.exit()

        self.log.debug("Python version: %s.%s.%s", python_version[0],
                      python_version[1], python_version[2])
        self.log.debug("Platform: %s", sys.platform)
        self.log.debug("Python executable location: %s", sys.executable)
        self.log.debug("32-bit Python? %s", sys.maxsize < 2**32)

        self.active_debugger = dict()

        self.config = dict()
        self.done = False  # todo
        self.machine_path = None
        self.asset_managers = dict()
        self.window = None
        self.window_manager = None
        self.pygame = False
        self.pygame_requested = False
        self.registered_pygame_handlers = dict()
        self.pygame_allowed_events = list()
        self.socket_thread = None
        self.receive_queue = Queue.Queue()
        self.sending_queue = Queue.Queue()
        self.crash_queue = Queue.Queue()
        self.modes = CaseInsensitiveDict()
        self.player_list = list()
        self.player = None
        self.HZ = 0
        self.next_tick_time = 0
        self.secs_per_tick = 0
        self.machine_vars = CaseInsensitiveDict()
        self.machine_var_monitor = False
        self.tick_num = 0
        self.delay = DelayManager()

        self._pc_assets_to_load = 0
        self._pc_total_assets = 0
        self.pc_connected = False

        Task.create(self._check_crash_queue)

        self.bcp_commands = {'ball_start': self.bcp_ball_start,
                             'ball_end': self.bcp_ball_end,
                             'config': self.bcp_config,
                             'error': self.bcp_error,
                             'get': self.bcp_get,
                             'goodbye': self.bcp_goodbye,
                             'hello': self.bcp_hello,
                             'machine_variable': self.bcp_machine_variable,
                             'mode_start': self.bcp_mode_start,
                             'mode_stop': self.bcp_mode_stop,
                             'player_added': self.bcp_player_add,
                             'player_score': self.bcp_player_score,
                             'player_turn_start': self.bcp_player_turn_start,
                             'player_variable': self.bcp_player_variable,
                             'reset': self.reset,
                             'set': self.bcp_set,
                             'shot': self.bcp_shot,
                             'switch': self.bcp_switch,
                             'timer': self.bcp_timer,
                             'trigger': self.bcp_trigger,
                            }

        # load the MPF config & machine defaults
        self.config = (
            Config.load_config_yaml(config=self.config,
                                    yaml_file=self.options['mcconfigfile']))

        # Find the machine_files location. If it starts with a forward or
        # backward slash, then we assume it's from the mpf root. Otherwise we
        # assume it's from the subfolder location specified in the
        # mpfconfig file location

        if (options['machinepath'].startswith('/') or
                options['machinepath'].startswith('\\')):
            machine_path = options['machinepath']
        else:
            machine_path = os.path.join(self.config['media_controller']['paths']
                                        ['machine_files'],
                                        options['machinepath'])

        self.machine_path = os.path.abspath(machine_path)

        # Add the machine folder to our path so we can import modules from it
        sys.path.append(self.machine_path)

        self.log.info("Machine folder: %s", machine_path)

        # Now find the config file location. Same as machine_file with the
        # slash uses to specify an absolute path

        if (options['configfile'].startswith('/') or
                options['configfile'].startswith('\\')):
            config_file = options['configfile']
        else:

            if not options['configfile'].endswith('.yaml'):
                options['configfile'] += '.yaml'

            config_file = os.path.join(self.machine_path,
                                       self.config['media_controller']['paths']
                                       ['config'],
                                       options['configfile'])

        self.log.debug("Base machine config file: %s", config_file)

        # Load the machine-specific config
        self.config = Config.load_config_yaml(config=self.config,
                                              yaml_file=config_file)

        mediacontroller_config_spec = '''
                        exit_on_disconnect: boolean|True
                        port: int|5050
                        '''

        self.config['media_controller'] = (
            Config.process_config(mediacontroller_config_spec,
                                  self.config['media_controller']))

        self.events = EventManager(self, setup_event_player=False)
        self.timing = Timing(self)

        # Load the media controller modules
        self.config['media_controller']['modules'] = (
            self.config['media_controller']['modules'].split(' '))
        self.log.info("Loading Modules...")
        for module in self.config['media_controller']['modules']:
            self.log.debug("Loading module: %s", module)
            module_parts = module.split('.')
            exec('self.' + module_parts[0] + '=' + module + '(self)')

            # todo there's probably a more pythonic way to do this, and I know
            # exec() is supposedly unsafe, but meh, if you have access to put
            # malicious files in the system folder then you have access to this
            # code too.

        self.start_socket_thread()

        self.events.post("init_phase_1")
        self.events.post("init_phase_2")
        self.events.post("init_phase_3")
        self.events.post("init_phase_4")
        self.events.post("init_phase_5")

        self.reset()

    def _check_crash_queue(self):
        try:
            crash = self.crash_queue.get(block=False)
        except Queue.Empty:
            yield 1000
        else:
            self.log.critical("MPF Shutting down due to child thread crash")
            self.log.critical("Crash details: %s", crash)
            self.done = True

    def reset(self, **kwargs):
        """Processes an incoming BCP 'reset' command."""
        self.player = None
        self.player_list = list()

        self.events.add_handler('assets_to_load',
                                self._bcp_client_asset_loader_tick)
        self.events.replace_handler('timer_tick', self.asset_loading_counter)

        self.events.post('mc_reset_phase_1')
        self.events.post('mc_reset_phase_2')
        self.events.post('mc_reset_phase_3')

    def get_window(self):
        """ Returns a reference to the onscreen display window.

        This method will set up a window if one doesn't exist yet. This method
        exists because there are several different modules and plugins which
        may want to use a window, but we don't know which combinations might
        be used, so we centralize the creation and management of an onscreen
        window here.

        """
        if not self.window:
            self.window_manager = window.WindowManager(self)
            self.window = self.window_manager.window

        return self.window

    def request_pygame(self):
        """Called by a module to let the system know it would like to use
        Pygame. We centralize the requests instead of letting each module do
        their own pygame.init() so we get it in one place and can get everthing
        initialized in the right order.

        Returns: True or False, depending on whether pygame is available or not.
        """

        if pygame and not self.pygame_requested:
            self.events.add_handler('init_phase_3', self._pygame_init)
            self.pygame_requested = True
            return True

        else:
            return False

    def _pygame_init(self):
        # performs the actual pygame initialization

        if not pygame:
            self.log.critical("Pygame is needed but not available. Please "
                              "install Pygame and try again.")
            raise Exception("Pygame is needed but not available. Please install"
                            " Pygame and try again.")

        if not self.pygame:
            self.log.debug("Initializing Pygame, version %s",
                           pygame.version.ver)

            pygame.init()
            self.pygame = True

            self.events.add_handler('timer_tick', self.get_pygame_events,
                                    priority=1000)
            self.events.add_handler('timer_tick', self.asset_loading_counter)

            self.events.post('pygame_initialized')

    def register_pygame_handler(self, event, handler):
        """Registers a method to be a handler for a certain type of Pygame
        event.

        Args:
            event: A string of the Pygame event name you're registering this
            handler for.
            handler: A method that will be called when this Pygame event is
            posted.
        """
        if event not in self.registered_pygame_handlers:
            self.registered_pygame_handlers[event] = set()

        self.registered_pygame_handlers[event].add(handler)
        self.pygame_allowed_events.append(event)

        self.log.debug("Adding Window event handler. Event:%s, Handler:%s",
                       event, handler)

        pygame.event.set_allowed(self.pygame_allowed_events)

    def get_pygame_events(self):
        """Gets (and dispatches) Pygame events. Automatically called every
        machine loop via the timer_tick event.
        """
        for event in pygame.event.get():
            if event.type in self.registered_pygame_handlers:
                for handler in self.registered_pygame_handlers[event.type]:

                    if (event.type == pygame.KEYDOWN or
                            event.type == pygame.KEYUP):
                        handler(event.key, event.mod)
                    else:
                        handler()

    def _process_command(self, bcp_command, **kwargs):
        self.log.debug("Processing command: %s %s", bcp_command, kwargs)


        # Can't use try/except KeyError here becasue there could be a KeyError
        # in the callback which we don't want it to swallow.
        if bcp_command in self.bcp_commands:
            self.bcp_commands[bcp_command](**kwargs)
        else:
            self.log.warning("Received invalid BCP command: %s", bcp_command)
            self.send('error', message='invalid command', command=bcp_command)


    def send(self, bcp_command, callback=None, **kwargs):
        """Sends a BCP command to the connected pinball controller.

        Args:
            bcp_command: String of the BCP command name.
            callback: Optional callback method that will be called when the
                command is sent.
            **kwargs: Optional additional kwargs will be added to the BCP
                command string.

        """
        self.sending_queue.put(bcp.encode_command_string(bcp_command,
                                                         **kwargs))
        if callback:
            callback()

    def send_dmd_frame(self, data):
        """Sends a DMD frame to the BCP client.

        Args:
            data: A 4096-length raw byte string.
        """

        dmd_string = 'dmd_frame?' + data
        self.sending_queue.put(dmd_string)

    def _timer_init(self):
        self.HZ = 30
        self.next_tick_time = time.time()
        self.secs_per_tick = 1.0 / self.HZ

    def timer_tick(self):
        """Called by the platform each machine tick based on self.HZ"""
        self.timing.timer_tick()  # notifies the timing module
        self.events.post('timer_tick')  # sends the timer_tick system event
        self.tick_num += 1
        Task.timer_tick()  # notifies tasks
        DelayManager.timer_tick()

    def run(self):
        """Main run loop."""
        self._timer_init()

        self.log.info("Starting the run loop at %sHz", self.HZ)

        start_time = time.time()
        loops = 0

        secs_per_tick = self.secs_per_tick

        self.next_tick_time = time.time()

        try:
            while self.done is False:
                time.sleep(0.001)

                self.get_from_queue()

                if self.next_tick_time <= time.time():  # todo change this
                    self.timer_tick()
                    self.next_tick_time += secs_per_tick
                    loops += 1

            self._do_shutdown()
            self.log.info("Target loop rate: %s Hz", self.HZ)
            self.log.info("Actual loop rate: %s Hz",
                          loops / (time.time() - start_time))

        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """Shuts down and exits the media controller.

        This method will also send the BCP 'goodbye' command to any connected
        clients.
        """
        self.socket_thread.stop()

    def _do_shutdown(self):
        if self.pygame:
            pygame.quit()

    def socket_thread_stopped(self):
        """Notifies the media controller that the socket thread has stopped."""
        self.done = True

    def start_socket_thread(self):
        """Starts the BCPServer socket thread."""
        self.socket_thread = BCPServer(self, self.receive_queue,
                                       self.sending_queue)
        self.socket_thread.daemon = True
        self.socket_thread.start()

    def get_from_queue(self):
        """Gets and processes all queued up incoming BCP commands."""
        while not self.receive_queue.empty():
            cmd, kwargs = bcp.decode_command_string(
                self.receive_queue.get(False))
            self._process_command(cmd, **kwargs)

    def bcp_hello(self, **kwargs):
        """Processes an incoming BCP 'hello' command."""
        try:
            if LooseVersion(kwargs['version']) == (
                    LooseVersion(version.__bcp_version__)):
                self.send('hello', version=version.__bcp_version__)
            else:
                self.send('hello', version='unknown protocol version')
        except KeyError:
            self.log.warning("Received invalid 'version' parameter with "
                             "'hello'")

    def bcp_goodbye(self, **kwargs):
        """Processes an incoming BCP 'goodbye' command."""
        if self.config['media_controller']['exit_on_disconnect']:
            self.socket_thread.sending_thread.stop()
            sys.exit()

    def bcp_mode_start(self, name=None, priority=0, **kwargs):
        """Processes an incoming BCP 'mode_start' command."""
        if not name:
            return
            #todo raise error

        if name == 'game':
            self._game_start()

        if name in self.modes:
            self.modes[name].start(priority=priority)

    def bcp_mode_stop(self, name, **kwargs):
        """Processes an incoming BCP 'mode_stop' command."""
        if not name:
            return
            #todo raise error

        if name == 'game':
            self._game_end()

        if name in self.modes:
            self.modes[name].stop()

    def bcp_error(self, **kwargs):
        """Processes an incoming BCP 'error' command."""
        self.log.warning('Received error command from client')

    def bcp_ball_start(self, **kwargs):
        """Processes an incoming BCP 'ball_start' command."""
        kwargs['player'] = kwargs.pop('player_num')

        self.events.post('ball_started', **kwargs)

    def bcp_ball_end(self, **kwargs):
        """Processes an incoming BCP 'ball_end' command."""
        self.events.post('ball_ended', **kwargs)

    def _game_start(self, **kargs):
        """Processes an incoming BCP 'game_start' command."""
        self.player = None
        self.player_list = list()
        self.num_players = 0
        self.events.post('game_started', **kargs)

    def _game_end(self, **kwargs):
        """Processes an incoming BCP 'game_end' command."""
        self.player = None
        self.events.post('game_ended', **kwargs)

    def bcp_player_add(self, player_num, **kwargs):
        """Processes an incoming BCP 'player_add' command."""

        if player_num > len(self.player_list):
            new_player = Player(self, self.player_list)

            self.events.post('player_add_success', num=player_num)

    def bcp_player_variable(self, name, value, prev_value, change, player_num,
                            **kwargs):
        """Processes an incoming BCP 'player_variable' command."""

        try:
            self.player_list[int(player_num)-1][name] = value
        except (IndexError, KeyError):
            pass

    def bcp_machine_variable(self, name, value, **kwargs):
        """Processes an incoming BCP 'machine_variable' command."""

        self._set_machine_var(name, value)

    def bcp_player_score(self, value, prev_value, change, player_num,
                         **kwargs):
        """Processes an incoming BCP 'player_score' command."""

        try:
            self.player_list[int(player_num)-1]['score'] = int(value)
        except (IndexError, KeyError):
            pass

    def bcp_player_turn_start(self, player_num, **kwargs):
        """Processes an incoming BCP 'player_turn_start' command."""

        self.log.debug("bcp_player_turn_start")

        if ((self.player and self.player.number != player_num) or
                not self.player):

            try:
                self.player = self.player_list[int(player_num)-1]
            except IndexError:
                self.log.error('Received player turn start for player %s, but '
                               'only %s player(s) exist',
                               player_num, len(self.player_list))

    def bcp_trigger(self, name, **kwargs):
        """Processes an incoming BCP 'trigger' command."""
        self.events.post(name, **kwargs)

    def bcp_switch(self, name, state, **kwargs):
        """Processes an incoming BCP 'switch' command."""
        if int(state):
            self.events.post('switch_' + name + '_active')
        else:
            self.events.post('switch_' + name + '_inactive')

    def bcp_get(self, **kwargs):
        """Processes an incoming BCP 'get' command by posting an event
        'bcp_get_<name>'. It's up to an event handler to register for that
        event and to send the response BCP 'set' command.

        """
        for name in Config.string_to_list(names):
            self.machine.events.post('bcp_get_{}'.format(name))

    def bcp_set(self, **kwargs):
        """Processes an incoming BCP 'set' command by posting an event
        'bcp_set_<name>' with a parameter value=<value>. It's up to an event
        handler to register for that event and to do something with it.

        Note that BCP set commands can contain multiple key/value pairs, and
        this method will post one event for each pair.

        """
        for k, v in kwargs.iteritems():
            self.machine.events.post('bcp_set_{}'.format(k), value=v)

    def bcp_shot(self, name, profile, state):
        """The MPF media controller uses triggers instead of shots for its
        display events, so we don't need to pay attention here."""
        pass

    def bcp_config(self, **kwargs):
        """Processes an incoming BCP 'config' command."""
        for k, v in kwargs.iteritems():
            if k.startswith('volume_'):
                self.bcp_set_volume(track=k.split('volume_')[1], value=v)

    def bcp_timer(self, name, action, **kwargs):
        """Processes an incoming BCP 'timer' command."""
        pass

    def bcp_set_volume(self, track, value):
        """Sets the volume based on an incoming BCP 'config' command.

        Args:
            track: String name of the track the volume will set.
            value: Float between 0 and 1 which represents the volume level to
                set.

        Note: At this time only the master volume can be set with this method.

        """
        if track == 'master':
            self.sound.set_volume(value)

        #if track in self.sound.tracks:
            #self.sound.tracks[track]

            # todo add per-track volume support to sound system

    def get_debug_status(self, debug_path):
        if self.options['loglevel'] > 10 or self.options['consoleloglevel'] > 10:
            return True

        class_, module = debug_path.split('|')

        try:
            if module in self.active_debugger[class_]:
                return True
            else:
                return False
        except KeyError:
            return False

    def _set_machine_var(self, name, value):
        try:
            prev_value = self.machine_vars[name]
        except KeyError:
            prev_value = None

        self.machine_vars[name] = value

        try:
            change = value-prev_value
        except TypeError:
            if prev_value != value:
                change = True
            else:
                change = False

        if change:
            self.log.debug("Setting machine_var '%s' to: %s, (prior: %s, "
                           "change: %s)", name, value, prev_value,
                           change)
            self.events.post('machine_var_' + name,
                                     value=value,
                                     prev_value=prev_value,
                                     change=change)

        if self.machine_var_monitor:
            for callback in self.monitors['machine_var']:
                callback(name=name, value=self.vars[name],
                         prev_value=prev_value, change=change)

    def _bcp_client_asset_loader_tick(self, total, remaining):
        self._pc_assets_to_load = int(remaining)
        self._pc_total_assets = int(total)

    def asset_loading_counter(self):

        if self.tick_num % 5 != 0:
            return

        if AssetManager.total_assets or self._pc_total_assets:
            # max because this could go negative at first
            percent = max(0, int(float(AssetManager.total_assets -
                                       self._pc_assets_to_load -
                                       AssetManager.loader_queue.qsize()) /
                                       AssetManager.total_assets * 100))
        else:
            percent = 100

        self.log.debug("Asset Loading Counter. PC remaining:{}, MC remaining:"
                       "{}, Percent Complete: {}".format(
                       self._pc_assets_to_load, AssetManager.loader_queue.qsize(),
                       percent))

        self.events.post('asset_loader',
                         total=AssetManager.loader_queue.qsize() +
                               self._pc_assets_to_load,
                         pc=self._pc_assets_to_load,
                         mc=AssetManager.loader_queue.qsize(),
                         percent=percent)

        if not AssetManager.loader_queue.qsize():

            if not self.pc_connected:
                self.events.post("waiting_for_client_connection")
                self.events.remove_handler(self.asset_loading_counter)

            elif not self._pc_assets_to_load:
                self.log.debug("Asset Loading Complete")
                self.events.post("asset_loading_complete")
                self.send('reset_complete')

                self.events.remove_handler(self.asset_loading_counter)

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
