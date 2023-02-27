"""PKONE serial communicator."""
import asyncio
import re
from packaging import version

from mpf.platforms.base_serial_communicator import BaseSerialCommunicator
from mpf.platforms.pkone.pkone_extension import PKONEExtensionBoard
from mpf.platforms.pkone.pkone_lightshow import PKONELightshowBoard

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform   # pylint: disable-msg=cyclic-import,unused-import

NANO_MIN_FW = '1.0'
EXTENSION_MIN_FW = '1.0'
LIGHTSHOW_MIN_FW = '1.0'


class PKONESerialCommunicator(BaseSerialCommunicator):

    """Handles the serial communication to the PKONE platform."""

    ignored_messages = ['PWD',  # Watchdog
                        ]

    __slots__ = ["part_msg", "send_queue", "remote_firmware", "remote_hardware_rev", "received_msg",
                 "max_messages_in_flight", "messages_in_flight", "send_ready"]

    # pylint: disable=too-many-arguments
    def __init__(self, platform: "PKONEHardwarePlatform", port, baud) -> None:
        """Initialize Serial Connection to PKONE Hardware.

        Args:
        ----
            platform(mpf.platforms.pkone.pkone.HardwarePlatform): the pkone hardware platform
            port: serial port
            baud: baud rate
        """
        self.send_queue = asyncio.Queue()
        self.remote_firmware = None
        self.remote_hardware_rev = None
        self.received_msg = b''
        self.max_messages_in_flight = 10
        self.messages_in_flight = 0

        self.send_ready = asyncio.Event()
        self.send_ready.set()

        super().__init__(platform, port, baud)

    async def _read_with_timeout(self, timeout):
        try:
            msg_raw = await asyncio.wait_for(self.readuntil(b'E'), timeout=timeout)
        except asyncio.TimeoutError:
            return ""
        return msg_raw.decode()

    async def _identify_connection(self):
        """Identify which controller this serial connection is talking to."""
        count = 0
        while True:
            if (count % 10) == 0:
                self.platform.debug_log("Sending 'PCN' command to port '%s'", self.port)

            count += 1
            self.writer.write('PCNE'.encode('ascii', 'replace'))
            msg = await self._read_with_timeout(.5)
            if msg.startswith('PCN'):
                break

            await asyncio.sleep(.5)

            if count == 100:
                raise AssertionError('No response from PKONE hardware on port {}'.format(self.port))

        # PCN (Determine connected controller board) reply is in the following format:
        # PCNF[Firmware rev]H[Hardware rev]E
        match = re.match('PCNF([0-9]+)H([0-9]+)E', msg)
        if not match:
            raise AssertionError(
                'Received an unexpected response. {} is not a recognized response to the PCN command.'.format(msg))

        self.remote_firmware = match[1][:-1] + '.' + match[1][-1]
        self.remote_hardware_rev = match[2]

        self.platform.log.info("Connected! "
                               "Board Type: PKONE Nano Controller, Firmware: %s, Hardware Rev: %s",
                               self.remote_firmware, self.remote_hardware_rev)

        self.machine.variables.set_machine_var("pkone_firmware", self.remote_firmware)
        '''machine_var: pkone_firmware

        desc: Holds the version number of the firmware for the Penny K Pinball PKONE controller that's connected.'''

        self.machine.variables.set_machine_var("pkone_hardware",
                                               "PKONE Nano Controller (rev {})".format(self.remote_hardware_rev))
        '''machine_var: pkone_hardware

        desc: Holds the model name and hardware revision number of the Penny K Pinball PKONE controller
        board that's connected.'''

        if version.parse(NANO_MIN_FW) > version.parse(self.remote_firmware):
            raise AssertionError('Firmware version mismatch. MPF requires '
                                 'the PKONE Nano Controller to be firmware {}, but yours is {}. '
                                 'Please update your firmware.'.
                                 format(NANO_MIN_FW, self.remote_firmware))

        # Reset the Nano controller and connected boards
        await self.reset_controller()

        # Determine what additional boards are connected to the Nano controller
        await self.query_pkone_boards()

        # Read the initial state of all switches
        await self.read_all_switches()

        self.platform.controller_connection = self

    async def reset_controller(self):
        """Reset the controller."""
        self.platform.debug_log('Resetting controller.')

        # this command returns several responses (one from each board, starting with the Nano controller)
        self.writer.write('PRSE'.encode())
        msg = ''
        while msg != 'PRSE' and not msg.startswith('PXX'):
            msg = (await self.readuntil(b'E')).decode()
            self.platform.debug_log("Got: {}".format(msg))

        if msg.startswith('PXX'):
            raise AssertionError('Received an error while resetting the controller: {}'.format(msg))

    async def query_pkone_boards(self):
        """Query the NANO processor to discover which additional boards are connected."""
        self.platform.debug_log('Querying PKONE boards...')

        # Determine connected add-on boards (PCB command)
        # Responses:
        # Extension board - PCB01XF11H1 = PCB[board number 0-7]XP[Y:48V, N: no 48V]F[firmware rev]H[hardware rev]
        # Lightshow board - PCB01LF10H1RGBW = PCB[board number 0-3]LF[firmware rev]H[hardware rev][firmware_type]
        # No board at the address: PCB[board number 0-7]N
        for address_id in range(8):
            self.writer.write('PCB{}E'.format(address_id).encode('ascii', 'replace'))
            msg = await self._read_with_timeout(.5)
            if msg == 'PCB{}NE'.format(address_id):
                self.platform.log.debug("No board at address ID {}".format(address_id))
                continue

            match = re.fullmatch('PCB([0-7])([XLN])F([0-9]+)H([0-9]+)(P[YN])?(RGB|RGBW)?E', msg)
            if not match:
                self.platform.log.warning("Received unexpected message from PKONE: {}".format(msg))

            if match.group(2) == "X":
                # Extension board
                firmware = match.group(3)[:-1] + '.' + match.group(3)[-1]
                hardware_rev = match.group(4)

                if version.parse(EXTENSION_MIN_FW) > version.parse(firmware):
                    raise AssertionError('Firmware version mismatch. MPF requires '
                                         'PKONE Extension boards to be at least firmware {}, but yours is {}. '
                                         'Please update your firmware.'.
                                         format(EXTENSION_MIN_FW, firmware))

                self.platform.debug_log('PKONE Extension Board {0}: '
                                        'Firmware: {1}, Hardware Rev: {2}'.format(address_id,
                                                                                  firmware, hardware_rev))

                self.platform.register_extension_board(PKONEExtensionBoard(address_id, firmware, hardware_rev))

            elif match.group(2) == "L":
                # Lightshow board
                firmware = match.group(3)[:-1] + '.' + match.group(3)[-1]
                hardware_rev = match.group(4)
                rgbw_firmware = match.group(6) == 'RGBW'

                if version.parse(LIGHTSHOW_MIN_FW) > version.parse(firmware):
                    raise AssertionError('Firmware version mismatch. MPF requires '
                                         'PKONE Lightshow boards to be at least firmware {}, but yours is {}. '
                                         'Please update your firmware.'.
                                         format(LIGHTSHOW_MIN_FW, firmware))

                self.platform.debug_log('PKONE Lightshow Board {0}: Firmware: {1} ({2}), '
                                        'Hardware Rev: {3}'.format(address_id,
                                                                   firmware,
                                                                   'RGBW' if rgbw_firmware else 'RGB',
                                                                   hardware_rev))

                self.platform.register_lightshow_board(PKONELightshowBoard(address_id,
                                                                           firmware,
                                                                           hardware_rev,
                                                                           rgbw_firmware))

            else:
                raise AttributeError("Unrecognized PKONE board type in message: {}".format(msg))

    async def read_all_switches(self):
        """Read the current state of all switches from the hardware."""
        self.platform.debug_log('Reading all switches.')
        for address_id in self.platform.pkone_extensions:
            self.writer.write('PSA{}E'.format(address_id).encode())
            msg = ''
            while not msg.startswith('PSA'):
                msg = (await self.readuntil(b'E')).decode()
                if not msg.startswith('PSA'):
                    self.platform.log.warning("Received unexpected message from PKONE: {}".format(msg))

            self.platform.process_received_message(msg)

    def _parse_msg(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find(b'E')

            # no more complete messages
            if pos == -1:
                break

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

            self.messages_in_flight -= 1
            if self.messages_in_flight <= self.max_messages_in_flight or not self.read_task:
                self.send_ready.set()
            if self.messages_in_flight < 0:
                self.log.warning("Received more messages than were sent! Resetting!")
                self.messages_in_flight = 0

            if not msg:
                continue

            if msg.decode() not in self.ignored_messages:
                self.platform.process_received_message(msg.decode())

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
        ----
            msg: Bytes of the message you want to send.
        """
        if self.debug:
            self.log.debug("%s sending: %s", self, msg)

        self.writer.write(msg.encode() + b'E')
