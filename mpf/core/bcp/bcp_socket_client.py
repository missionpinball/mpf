"""BCP socket client."""
import json
import logging
import urllib

import asyncio

from mpf._version import __version__, __bcp_version__
from mpf.core.bcp.bcp_client import BaseBcpClient


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


class BCPClientSocket(BaseBcpClient):

    """Parent class for a BCP client socket.

    (There can be multiple of these to connect to multiple BCP media controllers simultaneously.)

    Args:
        machine: The main MachineController object.
        name: String name this client.
        bcp: The bcp object.
    """

    def __init__(self, machine, name, bcp):
        """Initialise BCP client socket."""
        self.log = logging.getLogger('BCPClientSocket.' + str(name))
        self.log.debug('Setting up BCP Client...')

        super().__init__(machine, name, bcp)

        self._sender = None
        self._receiver = None
        self._send_goodbye = True
        self._stop_machine_on_stop = True
        self._receive_buffer = b''

        self._bcp_client_socket_commands = {'hello': self._receive_hello,
                                            'goodbye': self._receive_goodbye}

    def connect(self, config):
        """Actively connect to server."""
        config = self.machine.config_validator.validate_config(
            'bcp:connections', config, 'bcp:connections')

        self._stop_machine_on_stop = True

        self.machine.clock.loop.run_until_complete(self._setup_client_socket(config['host'], config['port']))

    @asyncio.coroutine
    def _setup_client_socket(self, client_host, client_port):
        """Set up the client socket."""
        self.log.info("Connecting to BCP Media Controller at %s:%s...",
                      client_host, client_port)

        while True:
            connector = self.machine.clock.open_connection(client_host, client_port)
            try:
                self._receiver, self._sender = yield from connector
            except ConnectionRefusedError:
                yield from asyncio.sleep(.1)
                continue

            break

        self.log.debug("Connected to remote BCP host %s:%s", client_host, client_port)

        self._start_reader()

    def accept_connection(self, receiver, sender):
        """Create client for incoming connection."""
        self._receiver = receiver
        self._sender = sender

        self._stop_machine_on_stop = False

        self._start_reader()

    def _start_reader(self):
        self.send_hello()
        self.read_task = self.machine.clock.loop.create_task(self._receive_loop())

    def stop(self):
        """Stop and shut down the socket client."""
        self.log.debug("Stopping socket client")

        if self._send_goodbye:
            self.send_goodbye()

        self.read_task.cancel()
        self._sender.close()

    def send(self, bcp_command, bcp_command_args):
        """Send a message to the BCP host.

        Args:
            bcp_command: command to send
            bcp_command_args: parameters to command
        """
        bcp_string = encode_command_string(bcp_command, **bcp_command_args)

        self.log.debug('Sending "%s"', bcp_string)
        try:
            self._sender.write((bcp_string + '\n').encode())
        except BrokenPipeError:
            self._handle_connection_close()

    def _handle_connection_close(self):
        # connection has been closed
        if self._stop_machine_on_stop:
            self.machine.stop()

    @asyncio.coroutine
    def _receive_loop(self):
        while True:
            should_continue = yield from self._receive()
            if not should_continue:
                break

    @asyncio.coroutine
    def _receive(self):
        """Receive loop."""
        try:
            buffer = yield from self._receiver.read(4096)
        except ConnectionResetError:
            # handle connection reset
            self._handle_connection_close()
            return False

        # handle EOF
        if not buffer:
            self._handle_connection_close()
            return False

        self._receive_buffer += buffer

        while True:
            # All this code exists to build complete messages since what we
            # get from the socket could be partial messages and/or could
            # include multiple messages.
            message, nl, leftovers = self._receive_buffer.partition(b'\n')

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
                self._receive_buffer = next_message

            else:  # no bytes in the message
                self._receive_buffer = leftovers
                self._process_command(message)

        return True

    def _process_command(self, message, rawbytes=None):
        self.log.debug('Received "%s"', message)

        cmd, kwargs = decode_command_string(message.decode())
        if rawbytes:
            kwargs['rawbytes'] = rawbytes

        if cmd in self._bcp_client_socket_commands:
            self._bcp_client_socket_commands[cmd](**kwargs)
        else:
            self.bcp.interface.process_bcp_message(cmd, kwargs, self)

    def _receive_hello(self, **kwargs):
        """Process incoming BCP 'hello' command."""
        self.log.debug('Received BCP Hello from host with kwargs: %s', kwargs)

    def _receive_goodbye(self):
        """Process incoming BCP 'goodbye' command."""
        self._send_goodbye = False
        self.stop()
        self.machine.bcp.transport.unregister_transport(self)
        self._handle_connection_close()

    def send_hello(self):
        """Send BCP 'hello' command."""
        self.send('hello', {"version": __bcp_version__,
                            "controller_name": 'Mission Pinball Framework',
                            "controller_version": __version__})

    def send_goodbye(self):
        """Send BCP 'goodbye' command."""
        self.send('goodbye', {})
