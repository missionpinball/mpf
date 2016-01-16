""" MPF plugin which sends events to sockets"""

import logging
import socket


class SocketClient(object):

    def __init__(self, machine):
        self.log = logging.getLogger('SocketEvents')
        self.machine = machine

        if 'socketserver' not in self.machine.config:
            return

        self.client_socket = None
        self.server_name = 'localhost'
        self.server_port = 5050
        self.config = None

        if 'host' in self.machine.config['socketserver']:
            self.server_name = self.machine.config['socketserver']['host']
        if 'port' in self.machine.config['socketserver']:
            self.server_port = self.machine.config['socketserver']['port']

        self.setup_client(self.server_name, self.server_port)

        self.machine.events.add_handler('shutdown', self.stop_client)

        if not self.client_socket:
            return

        self.process_config(self.machine.config['socketserver'])

    def process_config(self, config):
        """Processes the SocketEvents from the config.

        Args:
            config: Dictionary of the config to process.
        """
        # config is localized to SocketEvents

        self.config = config

        for event, settings in config.items():
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
        self.log.info("Stopping socket client")
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

        self.log.info("SOCKET SENDING: %s", message)

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


plugin_class = SocketClient
