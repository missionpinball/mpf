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
                        'SN:F',  #
                        'SL:P',  # Local Switch pass
                        'SL:F',
                        'LX:P',  # Lamp pass
                        'PX:P',  # Segment pass
                        'DN:P',  # Network driver pass
                        'DN:F',
                        'DL:P',  # Local driver pass
                        'DL:F',  # Local driver fail
                        'XX:F',  # Unrecognized command?
                        'R1:F',
                        'L1:P',
                        'GI:P',
                        'TL:P',
                        'TN:P',
                        'XO:P',  # Servo/Daughterboard Pass
                        'XX:U',
                        'XX:N',
                        ]

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

        self.received_msg = b''

        super().__init__(platform, port, baud)

    @asyncio.coroutine
    def _identify_connection(self):
        """Identify which processor this serial connection is talking to."""
        # keep looping and wait for an ID response

        msg = ''

        # send enough dummy commands to clear out any buffers on the FAST
        # board that might be waiting for more commands
        self.writer.write(((' ' * 256) + '\r').encode())

        while True:
            self.platform.debug_log("Sending 'ID:' command to port '%s'",
                                    self.port)
            self.writer.write('ID:\r'.encode())
            msg = (yield from self.readuntil(b'\r')).decode()
            if msg.startswith('ID:'):
                break

        # examples of ID responses
        # ID:DMD FP-CPU-002-1 00.87
        # ID:NET FP-CPU-002-2 00.85
        # ID:RGB FP-CPU-002-2 00.85

        try:
            self.remote_processor, self.remote_model, self.remote_firmware = (
                msg[3:].split())
        except ValueError:
            self.remote_processor, self.remote_model, = msg[3:].split()

        self.platform.debug_log("Received ID acknowledgement. Processor: %s, "
                                "Board: %s, Firmware: %s",
                                self.remote_processor, self.remote_model,
                                self.remote_firmware)

        if self.remote_processor == 'DMD':
            min_version = DMD_MIN_FW
            # latest_version = DMD_LATEST_FW
            self.dmd = True
        elif self.remote_processor == 'NET':
            min_version = NET_MIN_FW
            # latest_version = NET_LATEST_FW
        else:
            min_version = RGB_MIN_FW
            # latest_version = RGB_LATEST_FW

        if StrictVersion(min_version) > StrictVersion(self.remote_firmware):
            raise AssertionError('Firmware version mismatch. MPF requires'
                                 ' the {} processor to be firmware {}, but yours is {}'.
                                 format(self.remote_processor, min_version, self.remote_firmware))

        if self.remote_processor == 'NET' and self.platform.machine_type == 'fast':
            yield from self.query_fast_io_boards()

        self.platform.register_processor_connection(self.remote_processor, self)

    @asyncio.coroutine
    def query_fast_io_boards(self):
        """Query the NET processor to see if any FAST IO boards are connected.

        If so, queries the IO boards to log them and make sure they're the  proper firmware version.
        """
        self.writer.write('SA:\r'.encode())
        msg = ''
        while not msg.startswith('SA:'):
            msg = (yield from self.readuntil(b'\r')).decode()
            if not msg.startswith('SA:'):
                self.platform.debug_log("Got unexpected message from FAST: {}".format(msg))

        self.platform.process_received_message(msg)
        self.platform.debug_log('Querying FAST IO boards...')

        firmware_ok = True

        for board_id in range(self.platform.num_boards):
            self.writer.write('NN:{0}\r'.format(board_id).encode())
            msg = ''
            while not msg.startswith('NN:'):
                msg = (yield from self.readuntil(b'\r')).decode()
                if not msg.startswith('NN:'):
                    self.platform.debug_log("Got unexpected message from FAST: {}".format(msg))
            node_id, model, fw, dr, sw, _, _, _, _, _, _ = msg.split(',')
            node_id = node_id[3:]

            model = model.strip('\x00')

            # We only iterate known boards
            if not len(model):
                self.platform.log.critical("Got invalid board response from FAST: {}".format(msg))
                continue

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
        debug = self.platform.config['debug']
        if self.dmd:
            self.writer.write(b'BM:' + msg)
            if debug:
                self.platform.log.debug("Send: %s", "".join(" 0x%02x" % b for b in msg))

        else:
            self.writer.write(msg.encode() + b'\r')
            if debug and msg[0:2] != "WD":
                self.platform.log.debug("Send: %s", msg)

    def _parse_msg(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find(b'\r')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            if not msg:
                continue

            if msg.decode() not in self.ignored_messages:
                self.platform.process_received_message(msg.decode())
