"""BCP socket client."""
import json
import logging
import socket
import urllib
from mpf._version import __version__, __bcp_version__


def decode_command_string(bcp_string):
    """Decode a BCP command string into separate command and paramter parts.

    Args:
        bcp_string: The incoming UTF-8, URL encoded BCP command string.

    Returns:
        A tuple of the command string and a dictionary of kwarg pairs.

    Example:
        Input: trigger?name=hello&foo=Foo%20Bar
        Output: ('trigger', {'name': 'hello', 'foo': 'Foo Bar'})

    Note that BCP commands and parameter names are not case-sensitive and will
    be converted to lowercase. Parameter values are case sensitive, and case
    will be preserved.

    """
    bcp_command = urllib.parse.urlsplit(bcp_string)

    try:
        kwargs = urllib.parse.parse_qs(bcp_command.query)
        if 'json' in kwargs:
            kwargs = json.loads(kwargs['json'][0])
            return bcp_command.path.lower(), kwargs

    except AttributeError:
        kwargs = dict()

    for k, v in kwargs.items():
        if isinstance(v[0], str):
            if v[0].startswith('int:'):
                v[0] = int(v[0][4:])
            elif v[0].startswith('float:'):
                v[0] = float(v[0][6:])
            elif v[0].lower() == 'bool:true':
                v[0] = True
            elif v[0].lower() == 'bool:false':
                v[0] = False
            elif v[0] == 'NoneType:':
                v[0] = None
            else:
                v[0] = urllib.parse.unquote(v[0])

            kwargs[k] = v

    return (bcp_command.path.lower(),
            dict((k.lower(), v[0]) for k, v in kwargs.items()))


def encode_command_string(bcp_command, **kwargs):
    """Encode a BCP command and kwargs into a valid BCP command string.

    Args:
        bcp_command: String of the BCP command name.
        **kwargs: Optional pair(s) of kwargs which will be appended to the
            command.

    Returns:
        A string.

    Example:
        Input: encode_command_string('trigger', {'name': 'hello', 'foo': 'Bar'})
        Output: trigger?name=hello&foo=Bar

    Note that BCP commands and parameter names are not case-sensitive and will
    be converted to lowercase. Parameter values are case sensitive, and case
    will be preserved.

    """
    kwarg_string = ''
    json_needed = False

    for k, v in kwargs.items():
        if isinstance(v, dict) or isinstance(v, list):
            json_needed = True
            break

        value = urllib.parse.quote(str(v), '')

        if isinstance(v, bool):  # bool isinstance of int, so this goes first
            value = 'bool:{}'.format(value)
        elif isinstance(v, int):
            value = 'int:{}'.format(value)
        elif isinstance(v, float):
            value = 'float:{}'.format(value)
        elif v is None:
            value = 'NoneType:'

        kwarg_string += '{}={}&'.format(urllib.parse.quote(k.lower(), ''),
                                        value)

    kwarg_string = kwarg_string[:-1]

    if json_needed:
        kwarg_string = 'json={}'.format(json.dumps(kwargs))

    return str(urllib.parse.urlunparse(('', '', bcp_command.lower(), '',
                                        kwarg_string, '')))


class BCPClientSocket(object):

    """Parent class for a BCP client socket.

    (There can be multiple of these to connect to multiple BCP media controllers simultaneously.)

    Args:
        machine: The main MachineController object.
        name: String name this client.
        config: A dictionary containing the configuration for this client.
        bcp: The bcp object.
    """

    def __init__(self, machine, name, config, bcp):
        """Initialise BCP client socket."""
        self.log = logging.getLogger('BCPClientSocket.' + name)
        self.log.debug('Setting up BCP Client...')

        self.machine = machine
        self.name = name
        self.bcp = bcp

        self.config = self.machine.config_validator.validate_config(
            'bcp:connections', config, 'bcp:connections')

        self.socket = None
        self._send_goodbye = True
        self.receive_buffer = b''

        self.bcp_client_socket_commands = {'hello': self.receive_hello,
                                           'goodbye': self.receive_goodbye}

        self.setup_client_socket()

    def setup_client_socket(self):
        """Set up the client socket."""
        self.log.info("Connecting to BCP Media Controller at %s:%s...",
                      self.config['host'], self.config['port'])

        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        connected = False

        while not connected:
            try:
                self.socket.connect((self.config['host'], self.config['port']))
                self.log.debug("Connected to remote BCP host %s:%s",
                               self.config['host'], self.config['port'])

                self.machine.bcp.active_connections += 1
                connected = True

            except socket.error:
                pass

        self.machine.clock.schedule_socket_read_callback(self.socket, self._receive)
        self.send_hello()

    def stop(self):
        """Stop and shut down the socket client."""
        self.log.debug("Stopping socket client")

        if self._send_goodbye:
            self.send_goodbye()

        self.socket.close()
        self.machine.bcp.active_connections -= 1
        self.socket = None  # Socket threads will exit on this

    def send(self, message):
        """Send a message to the BCP host.

        Args:
            message: String of the message to send.
        """
        self.log.debug('Sending "%s"', message)
        try:
            self.socket.sendall((message + '\n').encode('utf-8'))
        except BrokenPipeError:
            self._handle_connection_close()

    def _handle_connection_close(self):
        # connection has been closed
        self.socket.close()
        self.machine.clock.unschedule_socket_read_callback(self.socket)
        self.machine.bcp.active_connections -= 1
        self.machine.done = True

    def _receive(self):
        """Receive loop."""
        try:
            buffer = self.socket.recv(4096)
        except ConnectionResetError:
            # handle connection reset
            self._handle_connection_close()
            return

        # handle EOF
        if not buffer:
            self._handle_connection_close()
            return

        self.receive_buffer += buffer

        while True:
            # All this code exists to build complete messages since what we
            # get from the socket could be partial messages and/or could
            # include multiple messages.
            message, nl, leftovers = self.receive_buffer.partition(b'\n')

            if not nl:  # \n not found. msg not complete. wait for later
                break

            if b'&bytes=' in message:
                message, bytes_needed = message.split(b'&bytes=')
                bytes_needed = int(bytes_needed)

                rawbytes = leftovers
                if len(rawbytes) < bytes_needed:
                    break

                rawbytes, next_message = (
                    rawbytes[0:bytes_needed],
                    rawbytes[bytes_needed:])

                self._process_command(message, rawbytes)
                self.receive_buffer = next_message

            else:  # no bytes in the message
                self.receive_buffer = leftovers
                self._process_command(message)

    def _process_command(self, message, rawbytes=None):
        self.log.debug('Received "%s"', message)

        cmd, kwargs = decode_command_string(message.decode())

        if cmd in self.bcp_client_socket_commands:
            self.bcp_client_socket_commands[cmd](**kwargs)
        else:
            self.bcp.process_bcp_message(cmd, kwargs, rawbytes)

    def receive_hello(self, **kwargs):
        """Process incoming BCP 'hello' command."""
        self.log.debug('Received BCP Hello from host with kwargs: %s', kwargs)

    def receive_goodbye(self):
        """Process incoming BCP 'goodbye' command."""
        self._send_goodbye = False
        self.stop()
        self.machine.bcp.remove_bcp_connection(self)

        self.machine.bcp.shutdown()
        self.machine.done = True

    def send_hello(self):
        """Send BCP 'hello' command."""
        self.send(encode_command_string('hello',
                                        version=__bcp_version__,
                                        controller_name='Mission Pinball Framework',
                                        controller_version=__version__))

    def send_goodbye(self):
        """Send BCP 'goodbye' command."""
        self.send('goodbye')
