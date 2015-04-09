""" MPF plugin which sends events to sockets"""
# socket_events.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf
import logging
import socket

def preload_check(machine):
    return True


class SocketClient(object):

    def __init__(self, machine):
        self.log = logging.getLogger('SocketEvents')
        self.machine = machine

        self.client_socket = None
        self.server_name = 'localhost'
        self.server_port = 5051
        self.config = None

        if 'SocketServer' in self.machine.config:
            if 'host' in self.machine.config['SocketServer']:
                self.server_name = self.machine.config['SocketServer']['host']
            if 'port' in self.machine.config['SocketServer']:
                self.server_port = self.machine.config['SocketServer']['port']

        self.setup_client(self.server_name, self.server_port)

        self.machine.events.add_handler('shutdown', self.stop_client)

        if not self.client_socket:
            return

        if 'SocketEvents' in self.machine.config:
            self.process_config(self.machine.config['SocketEvents'])

    def process_config(self, config):
        """Processes the SocketEvents from the config.

        Args:
            config: Dictionary of the config to process.
        """
        # config is localized to SocketEvents

        self.config = config

        for event, settings in config.iteritems():
            self.machine.events.add_handler(event, self._event_callback,
                                            settings=settings)

    def setup_client(self, host, port):
        """Sets up the socket client.

        Args:
            host: String of the host name.
            port: Int of the port name.
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM)
            self.client_socket.connect((host, port))

        except IOError:
            self.log.error('Could not connect to remote socket server. %s:%s',
                           host, port)

    def stop_client(self):
        """Stops and shuts down the socket client."""
        self.log.debug("Stopping socket client")
        self.client_socket.close()
        self.client_socket = None

    def _event_callback(self, settings, **kwargs):

        string = settings['string']

        # Are there any text variables to replace on the fly?
        # todo should this go here?
        if '%' in string:

            # first check for player vars (%var_name%)
            if self.machine.game and self.machine.game.player:
                for name, value in self.machine.game.player:
                    if '%' + name + '%' in string:
                        string = string.replace('%' + name + '%', str(value))

            # now check for single % which means event kwargs
            for kw in kwargs:
                if '%' + kw in string:
                    string = string.replace('%' + kw, str(kwargs[kw]))

        self.send_message(string)

    def send_message(self, message):
        """Sends a message to the remote socket host.

        Args:
            message: String of the message to send.
        """

        self.log.debug("SOCKET SENDING: %s", message)

        prepped_message = message + '\n'

        try:
            self.client_socket.send(prepped_message)

        except IOError:
            # maybe we got disconnected? Attempt to connect and send.
            self.setup_client(self.server_name, self.server_port)

            try:
                self.client_socket.send(prepped_message)
            except:
                self.log.error('Unable to send %s to remote socket server',
                               prepped_message)

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
