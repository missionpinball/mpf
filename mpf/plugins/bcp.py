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

# todo
'''
Done
====
hello
error
game_start
game_end
attract_start
attract_end
player_add?player=x (x is the player number that was just added)
ball_start?player=x&ball=x
ball_end


# to ignore commands
commands and param names are case-insensitive
id is up to 32 chars for shows, ball, etc.
auto resume

game_start
game_end
attract_start
attract_stop

machinemode_start
machinemode_stop


player_added?total_players=x

Player vars
===========
player_<var_name>?value=xxx&prev_value=xxx&change=xxx


player variable

mode starting
mode started
mode stopping
mode stopped

show starting
show started
show stopping
show stopped

shot

event

hello
goodbye

error

set
get

reset

ball starting
ball started
ball ending
ball ended

timer started
timer paused
timer tick
timer cancel
timer complete


'''

import logging
import socket
import threading
import urllib
import urlparse
from distutils.version import LooseVersion
from Queue import Queue

__bcp_version_info__ = ('1', '0alpha')
__bcp_version__ = '.'.join(__bcp_version_info__)


def preload_check(machine):
    return True


def decode_command_string(bcp_string):
    bcp_command = urlparse.urlsplit(bcp_string)
    kwargs = dict()
    if bcp_command.query:
        incoming_kwargs = urlparse.parse_qs(urllib.unquote(bcp_command.query))
        for name, value in incoming_kwargs.iteritems():
            kwargs[name] = value[0]

    return bcp_command.path, kwargs


def encode_command_string(bcp_command, **kwargs):
    if kwargs:
        kwargs = urllib.urlencode(kwargs)
        kwargs = urllib.quote(kwargs, '=')
    else:
        kwargs = None

    return urlparse.urlunparse((None, None, bcp_command, None, kwargs, None))


class BCP(object):

    def __init__(self, machine):
        if 'BCP_connections' not in machine.config:
            return

        self.log = logging.getLogger('BCP')
        self.machine = machine

        self.receive_queue = Queue()
        self.bcp_events = dict()
        self.connection_config = self.machine.config['BCP_connections']
        self.bcp_clients = list()

        self.bcp_receive_commands = {
                                    'error': self.bcp_error,
                                    'switch': self.bcp_switch,
                                    'dmd_frame': self.bcp_dmd_frame

                                    }

        self.setup_bcp_connections()

        if 'BCP_events' in self.machine.config:
            self.bcp_events = self.machine.config['BCP_events']
            self.process_bcp_events()

        self.machine.events.add_handler('timer_tick', self.get_bcp_messages)

        self.machine.modes.register_start_method(self.bcp_mode_start, 'Mode')

    def setup_bcp_connections(self):
        for name, settings in self.connection_config.iteritems():
            if 'host' not in settings:
                break
            elif 'port' not in settings:
                settings['port'] = self.machine.config['BCP']['port']

            self.bcp_clients.append(BCPClient(self.machine, name,
                                              settings['host'],
                                              settings['port'],
                                              self.receive_queue))

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
            for param, value in params.iteritems():

                # Are there any text variables to replace on the fly?
                # todo should this go here?
                if '%' in value:

                    # first check for player vars (%var_name%)
                    if self.machine.game and self.machine.game.player:
                        for name, val in self.machine.game.player:
                            if '%' + name + '%' in value:
                                value = value.replace('%' + name + '%', str(val))

                    # now check for single % which means event kwargs
                    for name, val in kwargs.iteritems():
                        if '%' + name in value:
                            params[param] = value.replace('%' + name, str(val))

            self.send(command, **params)

        else:
            self.send(command)

    def send(self, bcp_command, callback=None, **kwargs):
        bcp_string = encode_command_string(bcp_command, **kwargs)

        for client in self.bcp_clients:
            client.send(bcp_string)

        if callback:
            callback()

    def get_bcp_messages(self):

        while not self.receive_queue.empty():
            cmd, kwargs = self.receive_queue.get(False)

            self.log.info("Processing command: %s %s", cmd, kwargs)

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
        for client in self.bcp_clients:
            client.stop()

    def bcp_error(self, **kwargs):
        print "bcp_error", kwargs

    def bcp_mode_start(self, config, priority, mode, **kwargs):
        self.send('mode_start', name=mode.name, priority=priority)

        return self.bcp_mode_stop, mode.name

    def bcp_mode_stop(self, name, **kwargs):
        self.send('mode_stop', name=name)

    def bcp_switch(self, **kwargs):
        self.machine.switch_controller.process_switch(name=kwargs['name'],
                                                      state=int(kwargs['state']),
                                                      logical=True)

    def bcp_dmd_frame(self):
        pass



class BCPClient(object):

    def __init__(self, machine, name, host, port, queue):
        """Sets up a BCP socket client.

        Args:
            host: String of the host name.
            port: Integer of the port name.
        """

        self.machine = machine
        self.name = name
        self.server_name = host
        self.server_port = port
        self.queue = queue

        self.receive_thread = None

        self.client_socket = None

        self.log = logging.getLogger('BCPClient.' + self.name)

        self.bcp_commands = {
                             'hello': self.bcp_hello,
                             'goodbye': self.bcp_goodbye,
                            }

        self.setup_client()

    def send_hello(self):
        self.send('hello?version=' + __bcp_version__)

    def send_goodbye(self):
        self.send('goodbye')

    def setup_client(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)
            self.client_socket.connect((self.server_name, self.server_port))

            self.receive_thread = threading.Thread(target=self.receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            self.send_hello()

        except IOError:
            self.log.error('Could not connect to remote BCP server. %s:%s',
                           self.server_name, self.server_port)

    def stop(self):
        """Stops and shuts down the socket client."""
        self.log.info("Stopping socket client")

        self.send('goodbye')

        self.client_socket.close()
        self.client_socket = None

    def send(self, message):
        """Sends a message to the BCP host.

        Args:
            message: String of the message to send.
        """

        try:
            self.client_socket.sendall(message + '\n')
            self.log.info('>>>>>>>>>>>>>> Sending "%s"', message)

        except IOError:
            # maybe we got disconnected? Attempt to connect and send.
            self.setup_client()

            try:
                self.client_socket.sendall(prepped_message + '\n')
            except:
                self.log.error("Unable to send '%s' to BCP server", message)

    def receive_loop(self):
        while True:
            data = self.client_socket.recv(255)
            if data:
                messages = data.decode("utf-8").split("\n");
                for message in messages:
                    if message:
                        # do an initial processing here for connection-specific
                        # commands, including hello, goodbye
                        cmd, kwargs = decode_command_string(message)
                        print "***", cmd, kwargs

                        if cmd in self.bcp_commands:
                            self.bcp_commands[cmd](**kwargs)
                        else:
                            self.queue.put((cmd, kwargs))

    def bcp_hello(self, **kwargs):
        print "bcp_hello", kwargs

    def bcp_goodbye(self):
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
