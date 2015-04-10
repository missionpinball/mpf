"""Pygame-based media controller for MPF, based on the Backbox Control Protocol
(BCP) v1.0alpha"""
# media_controller.py
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
import os
import socket
import sys
import time
import threading
from distutils.version import LooseVersion
from Queue import Queue

import pygame

from mpf.media_controller.core import *

from mpf.system.config import Config
from mpf.system.events import EventManager
from mpf.system.timing import Timing
from mpf.system.tasks import Task, DelayManager
from mpf.game.player import Player
import mpf.plugins.bcp as bcp
import version

__bcp_version_info__ = ('1', '0')
__bcp_version__ = '.'.join(__bcp_version_info__)


class MediaController(object):

    def __init__(self, options):
        self.options = options

        self.log = logging.getLogger("MediaController")
        self.log.info("Media Controller Version %s", version.__version__)
        self.log.info("Backbox Control Protocol Version %s",
                      version.__version__)

        # Get the Python version for the log
        python_version = sys.version_info
        self.log.info("Python version: %s.%s.%s", python_version[0],
                      python_version[1], python_version[2])
        self.log.info("Platform: %s", sys.platform)
        self.log.info("Python executable location: %s", sys.executable)
        self.log.info("32-bit Python? %s", sys.maxsize < 2**32)

        self.config = dict()
        self.done = False  # todo
        self.machine_path = None
        self.asset_managers = dict()
        self.window = None
        self.pygame = False
        self.pygame_requested = False
        self.registered_pygame_handlers = dict()
        self.pygame_allowed_events = list()
        self.socket_thread = None
        self.queue = Queue()
        self.sending_queue = Queue()
        self.game_modes = dict()
        self.player_list = list()
        self.player = None

        self.bcp_commands = {'hello': self.bcp_hello,
                             'goodbye': self.bcp_goodbye,
                             'reset': self.bcp_reset,
                             'mode_start': self.bcp_mode_start,
                             'mode_stop': self.bcp_mode_stop,
                             'error': self.bcp_error,
                             'ball_start': self.bcp_ball_start,
                             'ball_end': self.bcp_ball_end,
                             'game_start': self.bcp_game_start,
                             'game_end': self.bcp_game_end,
                             'player_added': self.bcp_player_add,
                             'player_variable': self.bcp_player_variable,
                             'player_score': self.bcp_player_score,
                             'player_turn_start': self.bcp_player_turn_start,
                             'attract_start': self.bcp_attract_start,
                             'attract_stop': self.bcp_attract_stop
                            }

        # load the MPF config & machine defaults
        self.config = Config.load_config_yaml(config=self.config,
            yaml_file=self.options['mcconfigfile'])

        # Find the machine_files location. If it starts with a forward or
        # backward slash, then we assume it's from the mpf root. Otherwise we
        # assume it's from the subfolder location specified in the
        # mpfconfigfile location

        if (options['machinepath'].startswith('/') or
                options['machinepath'].startswith('\\')):
            machine_path = options['machinepath']
        else:
            machine_path = os.path.join(self.config['MediaController']['paths']
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
                                       self.config['MediaController']['paths']
                                       ['config'],
                                       options['configfile'])

        self.log.info("Base machine config file: %s", config_file)

        # Load the machine-specific config
        self.config = Config.load_config_yaml(config=self.config,
                                            yaml_file=config_file)

        self.events = EventManager(self)
        self.timing = Timing(self)

        # Load the media controller modules
        self.config['MediaController']['modules'] = (
            self.config['MediaController']['modules'].split(' '))
        for module in self.config['MediaController']['modules']:
            self.log.info("Loading module: %s", module)
            module_parts = module.split('.')
            exec('self.' + module_parts[0] + '=' + module + '(self)')

            # todo there's probably a more pythonic way to do this, and I know
            # exec() is supposedly unsafe, but meh, if you have access to put
            # malicious files in the system folder then you have access to this
            # code too.

        self.events.post("mc_init_phase_1")
        self.events.post("mc_init_phase_2")
        self.events.post("mc_init_phase_3")
        self.events.post("mc_init_phase_4")
        self.events.post("mc_init_phase_5")

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
            self.events.add_handler('mc_init_phase_3', self._pygame_init)
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

    def process_command(self, bcp_command, **kwargs):
        self.log.info("Processing command: %s %s", bcp_command, kwargs)

        # todo convert to try. Haven't done it yet though because I couldn't
        # figure out how to make it not swallow exceptions and it was getting
        # annoying to troubleshoot
        if bcp_command in self.bcp_commands:
            self.bcp_commands[bcp_command](**kwargs)
        else:
            self.log.warning("Received invalid BCP command: %s", bcp_command)
            self.send('error', message='invalid command', command=bcp_command)

    def send(self, bcp_command, callback=None, **kwargs):
        #print "send()", bcp.encode_command_string(bcp_command, **kwargs)
        self.sending_queue.put(bcp.encode_command_string(bcp_command,
                                                          **kwargs))

        if callback:
            callback()

    def timer_init(self):
        self.HZ = 30
        self.next_tick_time = time.time()
        self.secs_per_tick = 1.0 / self.HZ

    def timer_tick(self):
        """Called by the platform each machine tick based on self.HZ"""
        self.timing.timer_tick()  # notifies the timing module
        self.events.post('timer_tick')  # sends the timer_tick system event
        Task.timer_tick()  # notifies tasks
        DelayManager.timer_tick()

    def run(self):
        self.timer_init()

        self.log.info("Starting the run loop at %sHz", self.HZ)

        self.start_socket_thread()

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

            self.log.info("Target loop rate: %s Hz", self.HZ)
            self.log.info("Actual loop rate: %s Hz",
                          loops / (time.time() - start_time))

        except KeyboardInterrupt:
            pass

    def shutdown(self):
        if self.pygame:
            pygame.quit()

        self.send('goodbye', callback=self._do_shutdown)

    def _do_shutdown(self):
        self.done = True

    def start_socket_thread(self):
        self.socket_thread = BCPServer(self, self.queue, self.sending_queue)
        self.socket_thread.daemon = True
        self.socket_thread.start()

    def get_from_queue(self):

        #command = None
        while not self.queue.empty():
            cmd, kwargs = bcp.decode_command_string(self.queue.get(False))
            self.process_command(cmd, **kwargs)



        # try:
        #     command = self.queue.get(False)
        #
        # except:
        #     pass
        #
        # if command:
        #     cmd, kwargs = bcp.decode_command_string(command)
        #     self.process_command(cmd, **kwargs)

    def bcp_hello(self, **kwargs):
        try:
            if LooseVersion(kwargs['version']) == LooseVersion(__bcp_version__):
                self.send('hello', version=__bcp_version__)
            else:
                self.send('hello', version='unknown protocol version')
        except:
            self.log.warning("Received invalid 'version' parameter with 'hello'")
        #self.send('hello', version=__bcp_version__)

    def bcp_goodbye(self, **kwargs):
        pass

    def bcp_mode_start(self, name=None, priority=0, **kwargs):
        if not name:
            return
            #todo raise error

        #self.events.post('mode_' + name.lower() + '_start', **kwargs)

        if name in self.game_modes:
            self.game_modes[name].start(priority=priority)

    def bcp_mode_stop(self, name, **kwargs):
        if not name:
            return
            #todo raise error

        if name in self.game_modes:
            self.game_modes[name].stop()

        #self.events.post('mode_' + name.lower() + '_stop', **kwargs)

    def bcp_error(self, **kwargs):
        print "Received error command from client"

    def bcp_ball_start(self, **kwargs):
        self.events.post('ball_started', **kwargs)

    def bcp_ball_end(self, **kwargs):
        self.events.post('ball_ended', **kwargs)

    def bcp_game_start(self, **kargs):
        self.bcp_player_turn_start(player=1)
        self.events.post('game_started', **kargs)

    def bcp_game_end(self, **kwargs):
        self.player = None
        self.events.post('game_ended', **kwargs)

    def bcp_player_add(self, number, **kwargs):
        new_player = Player(self)
        self.player_list.append(new_player)
        new_player.score = 0

        self.events.post('player_add_success', num=number)

    def bcp_player_variable(self, name, value, prev_value, change, **kwargs):

        if self.player:
            self.player[name] = value

    def bcp_player_score(self, value, prev_value, change, **kwargs):

        if self.player:
            self.player['score'] = int(value)

    def bcp_attract_start(self, **kwargs):
        self.events.post('machineflow_Attract_start')

    def bcp_attract_stop(self, **kwargs):
        self.events.post('machineflow_Attract_stop')

    def bcp_player_turn_start(self, player, **kwargs):
        self.player = self.player_list[int(player)-1]

    def bcp_reset(self, **kwargs):
        self.player = None
        self.player_list = list()



class BCPServer(threading.Thread):

    def __init__(self, mc, receiving_queue, sending_queue):

        threading.Thread.__init__(self)
        self.mc = mc
        self.log = logging.getLogger('BCP')
        self.queue = receiving_queue
        self.sending_queue = sending_queue
        self.connection = None
        self.socket = None

        self.create_socket()

        self.sending_thread = threading.Thread(target=self.send_loop)
        self.sending_thread.daemon = True
        self.sending_thread.start()

    def create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        server_address = ('localhost', 5050)
        self.log.info('Starting up on %s port %s' % server_address)

        try:
            self.socket.bind(server_address)
        except IOError:
            print "Socket IOError"
            raise

        self.socket.listen(1)

    def run(self):

        while 1:
            self.log.info("Waiting for a connection...")
            self.mc.events.post('client_disconnected')
            self.connection, client_address = self.socket.accept()

            try:
                self.log.info("Received connection from: %s:%s",
                              client_address[0], client_address[1])
                self.mc.events.post('client_connected',
                                    address=client_address[0],
                                    port=client_address[1])

                # Receive the data in small chunks and retransmit it
                while 1:
                    data = self.connection.recv(255)
                    if data:
                        commands = data.decode("utf-8").split("\n");
                        for cmd in commands:
                            if cmd:
                                self.handle_command(cmd)
                    else:
                        print 'no more data from', client_address
                        break

            except:
                pass

            finally:
                self.connection.close()

    def handle_command(self, command):
        self.log.info("Received Command: %s", command)
        self.queue.put(command)

    def send_loop(self):
        while True:
            msg = self.sending_queue.get()
            try:
                self.connection.sendall(msg + '\n')
            except AttributeError:
                pass

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
