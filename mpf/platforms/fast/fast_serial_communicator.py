"""Fast serial communicator."""
import asyncio
from distutils.version import StrictVersion

from mpf.platforms.base_serial_communicator import BaseSerialCommunicator

# Minimum firmware versions needed for this module
from mpf.platforms.fast.fast_io_board import FastIoBoard

DMD_MIN_FW = '0.88'
NET_MIN_FW = '0.88'
RGB_MIN_FW = '0.87'
IO_MIN_FW = '0.87'

# DMD_LATEST_FW = '0.88'
# NET_LATEST_FW = '0.90'
# RGB_LATEST_FW = '0.88'
# IO_LATEST_FW = '0.89'


class FastSerialCommunicator(BaseSerialCommunicator):

    """Handles the serial communication to the FAST platform."""

    ignored_messages = ['RX:P',  # RGB Pass
                        'SN:P',  # Network Switch pass
                        'SL:P',  # Local Switch pass
                        'LX:P',  # Lamp pass
                        'PX:P',  # Segment pass
                        'DN:P',  # Network driver pass
                        'DL:P',  # Local driver pass
                        'XX:F',  # Unrecognized command?
                        'R1:F',
                        'L1:P',
                        'GI:P',
                        'TL:P',
                        'TN:P',
                        'XO:P',  # Servo/Daughterboard Pass
                        'XX:U',
                        'XX:N'
                        ]

    __slots__ = ["dmd", "remote_processor", "remote_model", "remote_firmware", "max_messages_in_flight",
                 "messages_in_flight", "ignored_messages_in_flight", "send_ready", "write_task", "received_msg",
                 "send_queue"]

    def __init__(self, platform, port, baud):
        """Initialise communicator.

        Args:
            platform(mpf.platforms.fast.fast.HardwarePlatform): the fast hardware platform
            port: serial port
            baud: baud rate
        """
        self.dmd = False

        self.remote_processor = None
        self.remote_model = None
        self.remote_firmware = 0.0
        self.max_messages_in_flight = 10
        self.messages_in_flight = 0
        self.ignored_messages_in_flight = {b'-N', b'/N', b'/L', b'-L'}

        self.send_ready = asyncio.Event(loop=platform.machine.clock.loop)
        self.send_ready.set()
        self.write_task = None

        self.received_msg = b''

        self.send_queue = asyncio.Queue(loop=platform.machine.clock.loop)

        super().__init__(platform, port, baud)

    def stop(self):
        """Stop and shut down this serial connection."""
        self.write_task.cancel()
        super().stop()

    @asyncio.coroutine
    def _read_with_timeout(self, timeout):
        msg_raw = yield from asyncio.wait([self.readuntil(b'\r')], timeout=timeout, loop=self.machine.clock.loop)
        if not msg_raw[0]:
            msg_raw[1].pop().cancel()
            return ""
        element = msg_raw[0].pop()
        return (yield from element).decode()

    @asyncio.coroutine
    def _identify_connection(self):
        """Identify which processor this serial connection is talking to."""
        # keep looping and wait for an ID response

        msg = ''

        # send enough dummy commands to clear out any buffers on the FAST
        # board that might be waiting for more commands
        self.writer.write(((' ' * 256 * 4) + '\r').encode())

        while True:
            self.platform.debug_log("Sending 'ID:' command to port '%s'",
                                    self.port)
            self.writer.write('ID:\r'.encode())
            msg = yield from self._read_with_timeout(.5)

            # ignore XX replies here.
            while msg.startswith('XX:'):
                msg = yield from self._read_with_timeout(.5)

            if msg.startswith('ID:'):
                break

            yield from asyncio.sleep(.5, loop=self.machine.clock.loop)

        # examples of ID responses
        # ID:DMD FP-CPU-002-1 00.87
        # ID:NET FP-CPU-002-2 00.85
        # ID:RGB FP-CPU-002-2 00.85

        try:
            self.remote_processor, self.remote_model, self.remote_firmware = (
                msg[3:].split())
        except ValueError:
            self.remote_processor, self.remote_model, = msg[3:].split()

        self.platform.log.info("Connected! Processor: %s, "
                               "Board Type: %s, Firmware: %s",
                               self.remote_processor, self.remote_model,
                               self.remote_firmware)

        self.machine.set_machine_var("fast_{}_firmware".format(self.remote_processor.lower()), self.remote_firmware)
        '''machine_var: fast_(x)_firmware

        desc: Holds the version number of the firmware for the processor on
        the FAST Pinball controller that's connected. The "x" is replaced with
        either "dmd", "net", or "rgb", one for each processor that's attached.
        '''

        self.machine.set_machine_var("fast_{}_model".format(self.remote_processor.lower()), self.remote_model)

        '''machine_var: fast_(x)_model

        desc: Holds the model number of the board for the processor on
        the FAST Pinball controller that's connected. The "x" is replaced with
        either "dmd", "net", or "rgb", one for each processor that's attached.
        '''

        if self.remote_processor == 'DMD':
            min_version = DMD_MIN_FW
            # latest_version = DMD_LATEST_FW
            self.dmd = True
            self.max_messages_in_flight = self.platform.config['dmd_buffer']
            self.platform.debug_log("Setting DMD buffer size: %s",
                                    self.max_messages_in_flight)
        elif self.remote_processor == 'NET':
            min_version = NET_MIN_FW
            # latest_version = NET_LATEST_FW
            self.max_messages_in_flight = self.platform.config['net_buffer']
            self.platform.debug_log("Setting NET buffer size: %s",
                                    self.max_messages_in_flight)
        elif self.remote_processor == 'RGB':
            min_version = RGB_MIN_FW
            # latest_version = RGB_LATEST_FW
            self.max_messages_in_flight = self.platform.config['rgb_buffer']
            self.platform.debug_log("Setting RGB buffer size: %s",
                                    self.max_messages_in_flight)
        else:
            raise AttributeError("Unrecognized FAST processor type: {}".format(self.remote_processor))

        if StrictVersion(min_version) > StrictVersion(self.remote_firmware):
            raise AssertionError('Firmware version mismatch. MPF requires'
                                 ' the {} processor to be firmware {}, but yours is {}'.
                                 format(self.remote_processor, min_version, self.remote_firmware))

        if self.remote_processor == 'NET' and self.platform.machine_type == 'fast':
            yield from self.query_fast_io_boards()

        self.platform.register_processor_connection(self.remote_processor, self)

        self.write_task = self.machine.clock.loop.create_task(self._socket_writer())
        self.write_task.add_done_callback(self._done)

    @asyncio.coroutine
    def query_fast_io_boards(self):
        """Query the NET processor to see if any FAST IO boards are connected.

        If so, queries the IO boards to log them and make sure they're the  proper firmware version.
        """
        # reset CPU early
        if StrictVersion(self.remote_firmware) >= StrictVersion("1.03"):
            self.platform.debug_log('Resetting NET CPU.')
            self.writer.write('BC:\r'.encode())
            msg = ''
            while not msg.startswith('BC:P\r'):
                msg = (yield from self.readuntil(b'\r')).decode()
            yield from asyncio.sleep(.1, loop=self.machine.clock.loop)
        else:
            self.platform.log.warning("Not resetting FAST NET because firmware is currently broken.")

        self.platform.debug_log('Reading all switches.')
        self.writer.write('SA:\r'.encode())
        msg = ''
        while not msg.startswith('SA:'):
            msg = (yield from self.readuntil(b'\r')).decode()
            if not msg.startswith('SA:'):
                self.platform.log.warning("Got unexpected message from FAST: {}".format(msg))

        self.platform.process_received_message(msg)
        self.platform.debug_log('Querying FAST IO boards...')

        firmware_ok = True

        for board_id in range(128):
            self.writer.write('NN:{:02X}\r'.format(board_id).encode())
            msg = ''
            while not msg.startswith('NN:'):
                msg = (yield from self.readuntil(b'\r')).decode()
                if not msg.startswith('NN:'):
                    self.platform.debug_log("Got unexpected message from FAST: {}".format(msg))

            if msg == 'NN:F\r':
                break

            node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
            node_id = node_id[3:]

            model = model.strip('\x00')

            # Iterate as many boards as possible
            if not model or model == '!Node Not Found!':
                break

            self.platform.register_io_board(FastIoBoard(int(node_id, 16), model, fw, int(sw, 16), int(dr, 16)))

            self.platform.debug_log('Fast IO Board {0}: Model: {1}, '
                                    'Firmware: {2}, Switches: {3}, '
                                    'Drivers: {4}'.format(node_id,
                                                          model, fw,
                                                          int(sw, 16),
                                                          int(dr, 16)))

            if StrictVersion(IO_MIN_FW) > str(fw):
                self.platform.log.critical("Firmware version mismatch. MPF "
                                           "requires the IO boards to be firmware {0}, but "
                                           "your Board {1} ({2}) is v{3}".format(IO_MIN_FW, node_id, model, fw))
                firmware_ok = False

        if not firmware_ok:
            raise AssertionError("Exiting due to IO board firmware mismatch")

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
            msg: String of the message you want to send. THe <CR> character will
                be added automatically.

        """
        self.send_queue.put_nowait(msg)

    def _send(self, msg):
        debug = self.platform.config['debug']
        if self.dmd:
            self.writer.write(b'BM:' + msg)
            if debug:
                self.platform.log.debug("Send: %s", "".join(" 0x%02x" % b for b in msg))

        else:
            self.messages_in_flight += 1
            if self.messages_in_flight > self.max_messages_in_flight:
                self.send_ready.clear()

                self.log.debug("Enabling Flow Control for %s connection. "
                               "Messages in flight: %s, Max setting: %s",
                               self.remote_processor,
                               self.messages_in_flight,
                               self.max_messages_in_flight)

            self.writer.write(msg.encode() + b'\r')
            if debug and msg[0:2] != "WD":
                self.platform.log.debug("Send: %s", msg)

    @asyncio.coroutine
    def _socket_writer(self):
        while True:
            msg = yield from self.send_queue.get()
            try:
                yield from asyncio.wait_for(self.send_ready.wait(), 1.0, loop=self.machine.clock.loop)
            except asyncio.TimeoutError:
                self.log.warning("Port %s was blocked for more than 1s. Reseting send queue! If this happens "
                                 "frequently report a bug!", self.port)
                self.messages_in_flight = 0
                self.send_ready.set()

            self._send(msg)

    def _parse_msg(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find(b'\r')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            if msg[:2] not in self.ignored_messages_in_flight:

                self.messages_in_flight -= 1
                if self.messages_in_flight <= self.max_messages_in_flight or not self.read_task:
                    self.send_ready.set()
                if self.messages_in_flight < 0:
                    self.log.warning("Port %s received more messages than "
                                     "were sent! Resetting!",
                                     self.remote_processor)
                    self.messages_in_flight = 0

            if not msg:
                continue

            if msg.decode() not in self.ignored_messages:
                self.platform.process_received_message(msg.decode())
