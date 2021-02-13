"""PKONE serial communicator."""
import asyncio
import re
from distutils.version import StrictVersion

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

    __slots__ = ["part_msg", "send_queue", "remote_firmware", "remote_hardware_rev"]

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
        super().__init__(platform, port, baud)

    def stop(self):
        """Stop and shut down this serial connection."""
        super().stop()

    async def _identify_connection(self):
        """Identify which processor this serial connection is talking to."""

        count = 0
        while True:
            if (count % 10) == 0:
                self.platform.debug_log("Sending 'PCN' command to port '%s'", self.port)

            count += 1
            self.writer.write('PCNE'.encode())
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

        desc: Holds the version number of the firmware for the Penny K Pinball PKONE 
        controller that's connected.
        '''

        self.machine.variables.set_machine_var("pkone_hardware",
                                               "PKONE Nano Controller (rev {})".format(self.remote_model))

        '''machine_var: pkone_hardware

        desc: Holds the model name and hardware revision number of the Penny K Pinball PKONE controller board 
        that's connected.
        '''

        if StrictVersion(NANO_MIN_FW) > StrictVersion(self.remote_firmware):
            raise AssertionError('Firmware version mismatch. MPF requires '
                                 'the PKONE Nano Controller to be firmware {}, but yours is {}. '
                                 'Please update your firmware.'.
                                 format(NANO_MIN_FW, self.remote_firmware))

        await self.query_pkone_boards()

        self.platform.controller_connection = self

    async def query_pkone_boards(self):
        """Query the NANO processor to discover which additional boards are connected.
        """
        self.platform.debug_log('Querying PKONE boards...')

        # Determine connected add-on boards (PCB command)
        # Responses:
        # Extension board - PCB01XF11H1 = PCB[board number 0-7]XP[Y:48V, N: no 48V]F[firmware rev]H[hardware rev]
        # Lightshow board - PCB01LF10H1 = PCB[board number 0-3]LF[firmware rev]H[hardware rev]
        # No board at the address: PCB[board number 0-7]N
        for address_id in range(8):
            self.writer.write('PCB{:02d}E'.format(address_id).encode())
            msg = await self.readuntil('E')

            match = re.match('PCB([0-7])([XLN])F([0-9]+)H([0-9]+)E', msg)
            if not match:
                self.platform.log.warning("Received unexpected message from PKONE: {}".format(msg))

            if match[2] == "X":
                # Extension board
                firmware = match[3][:-1] + '.' + match[3][-1]
                hardware_rev = match[4]

                if StrictVersion(EXTENSION_MIN_FW) > StrictVersion(firmware):
                    raise AssertionError('Firmware version mismatch. MPF requires '
                                         'PKONE Extension boards to be at least firmware {}, but yours is {}. '
                                         'Please update your firmware.'.
                                         format(EXTENSION_MIN_FW, firmware))

                self.platform.debug_log('PKONE Extension Board {0}: '
                                        'Firmware: {1}, Hardware Rev: {2}'.format(address_id,
                                                                                  firmware, hardware_rev))

                self.platform.register_extension_board(PKONEExtensionBoard(address_id, firmware, hardware_rev))

            elif match[2] == "L":
                # Lightshow board
                firmware = match[3][:-1] + '.' + match[3][-1]
                hardware_rev = match[4]

                if StrictVersion(LIGHTSHOW_MIN_FW) > StrictVersion(firmware):
                    raise AssertionError('Firmware version mismatch. MPF requires '
                                         'PKONE Lightshow boards to be at least firmware {}, but yours is {}. '
                                         'Please update your firmware.'.
                                         format(LIGHTSHOW_MIN_FW, firmware))

                self.platform.debug_log('PKONE Lightshow Board {0}: '
                                        'Firmware: {1}, Hardware Rev: {2}'.format(address_id,
                                                                                  firmware, hardware_rev))

                self.platform.register_lighshow_board(PKONELightshowBoard(address_id, firmware, hardware_rev))

            elif match[2] == "N":
                # No board at address
                continue
            else:
                raise AttributeError("Unrecognized PKONE board type in message: {}".format(msg))

    def _parse_msg(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find('E')

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
                self.platform.process_received_message(msg.decode(), self.remote_processor)

    def send(self, msg):
        """Send a message to the remote processor over the serial connection.

        Args:
        ----
            msg: Bytes of the message you want to send.
        """
        if self.debug:
            self.log.debug("%s sending: %s", self, msg)
        self.writer.write(msg)
