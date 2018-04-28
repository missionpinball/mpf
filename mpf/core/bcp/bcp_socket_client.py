"""BCP socket client."""
import json
from urllib.parse import urlsplit, parse_qs, quote, unquote, urlunparse

import asyncio

from mpf._version import __version__, __bcp_version__
from mpf.core.bcp.bcp_client import BaseBcpClient


class MpfJSONEncoder(json.JSONEncoder):

    """Encoder which by default encodes to string."""

    # pylint: disable-msg=method-hidden
    def default(self, o):
        """Encode to string."""
        return str(o)


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
    bcp_command = urlsplit(bcp_string)

    try:
        kwargs = parse_qs(bcp_command.query, keep_blank_values=True)
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
                v[0] = unquote(v[0])

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
        if isinstance(v, (dict, list)):
            json_needed = True
            break

        value = quote(str(v), '')

        if isinstance(v, bool):  # bool isinstance of int, so this goes first
            value = 'bool:{}'.format(value)
        elif isinstance(v, int):
            value = 'int:{}'.format(value)
        elif isinstance(v, float):
            value = 'float:{}'.format(value)
        elif v is None:
            value = 'NoneType:'
        else:  # cast anything else as a string
            value = str(value)

        kwarg_string += '{}={}&'.format(quote(k.lower(), ''),
                                        value)

    kwarg_string = kwarg_string[:-1]

    if json_needed:
        kwarg_string = 'json={}'.format(json.dumps(kwargs, cls=MpfJSONEncoder))

    return str(urlunparse(('', '', bcp_command.lower(), '', kwarg_string, '')))


class AsyncioBcpClientSocket():

    """Simple asyncio bcp client."""

    def __init__(self, sender, receiver):
        """Initialise BCP client socket."""
        self._sender = sender
        self._receiver = receiver
        self._receive_buffer = b''

    # pylint: disable-msg=inconsistent-return-statements
    @asyncio.coroutine
    def read_message(self):
        """Read the next message."""
        while True:
            message = yield from self._receiver.readline()

            # handle EOF
            if not message:
                raise BrokenPipeError()

            # strip newline
            message = message[0:-1]

            if b'&bytes=' in message:
                message, bytes_needed = message.split(b'&bytes=')
                bytes_needed = int(bytes_needed)

                rawbytes = yield from self._receiver.readexactly(bytes_needed)

                message_obj = self._process_command(message, rawbytes)

            else:  # no bytes in the message
                message_obj = self._process_command(message)

            if message_obj:
                return message_obj

    def send(self, bcp_command, kwargs):
        """Send a message to the BCP host.

        Args:
            bcp_command: command to send
            kwargs: parameters to command
        """
        bcp_string = encode_command_string(bcp_command, **kwargs)
        self._sender.write((bcp_string + '\n').encode())

    @asyncio.coroutine
    def wait_for_response(self, bcp_command):
        """Wait for a command and ignore all others."""
        while True:
            cmd, args = yield from self.read_message()
            if cmd == "reset":
                self.send("reset_complete", {})
                continue
            if cmd == bcp_command:
                return cmd, args

    @staticmethod
    def _process_command(message, rawbytes=None):
        cmd, kwargs = decode_command_string(message.decode())
        if rawbytes:
            kwargs['rawbytes'] = rawbytes

        return cmd, kwargs


class BCPClientSocket(BaseBcpClient):

    """MPF version of the AsyncioBcpClientSocket.

    (There can be multiple of these to connect to multiple BCP media controllers simultaneously.)

    Args:
        machine: The main MachineController object.
        name: String name this client.
        bcp: The bcp object.
    """

    def __init__(self, machine, name, bcp):
        """Initialise BCP client socket."""
        self.module_name = 'BCPClientSocket.{}'.format(name)
        self.config_name = 'bcp_client'

        super().__init__(machine, name, bcp)

        self._sender = None
        self._receiver = None
        self._send_goodbye = True
        self._receive_buffer = b''

        self._bcp_client_socket_commands = {'hello': self._receive_hello,
                                            'goodbye': self._receive_goodbye}

    def __repr__(self):
        """Return str representation."""
        return self.module_name

    def connect(self, config):
        """Actively connect to server."""
        config = self.machine.config_validator.validate_config(
            'bcp:connections', config, 'bcp:connections')

        # return a future
        return self._setup_client_socket(config['host'], config['port'], config.get('required'))

    @asyncio.coroutine
    def _setup_client_socket(self, client_host, client_port, required=True):
        """Set up the client socket."""
        self.info_log("Connecting BCP to '%s' at %s:%s...",
                      self.name, client_host, client_port)

        while True:
            connector = self.machine.clock.open_connection(client_host, client_port)
            try:
                self._receiver, self._sender = yield from connector
            except (ConnectionRefusedError, OSError):
                if required:
                    yield from asyncio.sleep(.1)
                    continue
                else:
                    self.info_log("No BCP connection made to '%s' %s:%s",
                                  self.name, client_host, client_port)
                    return False

            break

        self.info_log("Connected BCP to '%s' %s:%s", self.name, client_host, client_port)

        self.send_hello()
        return True

    def accept_connection(self, receiver, sender):
        """Create client for incoming connection."""
        self._receiver = receiver
        self._sender = sender

        self.send_hello()

    def stop(self):
        """Stop and shut down the socket client."""
        self.debug_log("Stopping socket client")

        if self._send_goodbye:
            self.send_goodbye()

        self._sender.close()

    def send(self, bcp_command, kwargs):
        """Send a message to the BCP host.

        Args:
            bcp_command: command to send
            kwargs: parameters to command
        """
        try:
            bcp_string = encode_command_string(bcp_command, **kwargs)
        # pylint: disable-msg=broad-except
        except Exception as e:
            self.warning_log("Failed to encode bcp_command %s with args %s. %s", bcp_command, kwargs, e)
            return

        if self.debug_log:
            self.debug_log('Sending "%s"', bcp_string)

        if hasattr(self._sender.transport, "is_closing") and self._sender.transport.is_closing():
            self.warning_log("Failed to write to bcp since transport is closing. Transport %s", self._sender.transport)
            return
        self._sender.write((bcp_string + '\n').encode())

    # pylint: disable-msg=inconsistent-return-statements
    @asyncio.coroutine
    def read_message(self):
        """Read the next message."""
        while True:
            message = yield from self._receiver.readline()

            # handle EOF
            if not message:
                raise BrokenPipeError()

            # strip newline
            message = message[0:-1]

            if b'&bytes=' in message:
                message, bytes_needed = message.split(b'&bytes=')
                bytes_needed = int(bytes_needed)

                rawbytes = yield from self._receiver.readexactly(bytes_needed)

                message_obj = self._process_command(message, rawbytes)

            else:  # no bytes in the message
                message_obj = self._process_command(message)

            if message_obj:
                return message_obj

    def _process_command(self, message, rawbytes=None):
        if self.debug_log:
            self.debug_log('Received "%s"', message)

        cmd, kwargs = decode_command_string(message.decode())
        if rawbytes:
            kwargs['rawbytes'] = rawbytes

        if cmd in self._bcp_client_socket_commands:
            self._bcp_client_socket_commands[cmd](**kwargs)
            return None
        else:
            return cmd, kwargs

    def _receive_hello(self, **kwargs):
        """Process incoming BCP 'hello' command."""
        self.debug_log('Received BCP Hello from host with kwargs: %s', kwargs)

    def _receive_goodbye(self):
        """Process incoming BCP 'goodbye' command."""
        self._send_goodbye = False
        self.stop()

    def send_hello(self):
        """Send BCP 'hello' command."""
        self.send('hello', {"version": __bcp_version__,
                            "controller_name": 'Mission Pinball Framework',
                            "controller_version": __version__})

    def send_goodbye(self):
        """Send BCP 'goodbye' command."""
        self.send('goodbye', {})
