"""PKONE serial communicator."""
import asyncio
import re
from typing import TYPE_CHECKING

from packaging import version

from mpf.platforms.base_serial_communicator import BaseSerialCommunicator
from mpf.platforms.pkone.pkone_ex2 import PKONEEX2Board
from mpf.platforms.pkone.pkone_switch import PKONESwitchBoard
from mpf.platforms.pkone.pkone_lightshow import PKONELightshowBoard


if TYPE_CHECKING:
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform   # pylint: disable-msg=cyclic-import,unused-import

EX2_USB_MIN_FW = '1.0'
EX2_MIN_FW = '1.0'
SWITCH_MIN_FW = '3.0'
LIGHTSHOW_MIN_FW = '1.0'
STARTUP_TIMEOUT = 2.0
MAX_MESSAGE_LENGTH = 1024


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
        except asyncio.IncompleteReadError as exc:
            raise AssertionError("PKONE disconnected during startup on {}".format(self.port)) from exc
        try:
            return msg_raw.decode('ascii')
        except UnicodeDecodeError as exc:
            raise AssertionError("Non-ASCII PKONE response on {}".format(self.port)) from exc

    async def _wait_for_response(self, prefix, context, timeout=STARTUP_TIMEOUT):
        """Wait for a startup reply within one deadline, even if other messages arrive."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise AssertionError("Timed out {} on {}".format(context, self.port))
            msg = await self._read_with_timeout(remaining)
            if not msg:
                raise AssertionError("Timed out {} on {}".format(context, self.port))
            if msg.startswith('PXX'):
                raise AssertionError("PKONE error {} while {}".format(msg, context))
            if msg.startswith(prefix):
                return msg
            self.platform.debug_log("Ignoring startup message while %s: %s", context, msg)

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
        match = re.fullmatch('PCNF([0-9]+)H([0-9]+)E', msg)
        if not match:
            raise AssertionError(
                'Received an unexpected response. {} is not a recognized response to the PCN command.'.format(msg))

        self.remote_firmware = match[1][:-1] + '.' + match[1][-1]
        self.remote_hardware_rev = match[2]

        self.platform.log.info("Connected! "
                               "Board Type: PKONE EX2 USB connection, Firmware: %s, Hardware Rev: %s",
                               self.remote_firmware, self.remote_hardware_rev)

        self.machine.variables.set_machine_var("pkone_firmware", self.remote_firmware)
        '''machine_var: pkone_firmware

        desc: Holds the version number returned by the PKONE EX2 USB connection.'''

        self.machine.variables.set_machine_var("pkone_hardware",
                                               "PKONE EX2 (rev {})".format(self.remote_hardware_rev))
        '''machine_var: pkone_hardware

        desc: Holds the model name and hardware revision of the connected PKONE EX2.'''

        if version.parse(EX2_USB_MIN_FW) > version.parse(self.remote_firmware):
            raise AssertionError('Firmware version mismatch. MPF requires '
                                 'the connected PKONE EX2 to be firmware {}, but yours is {}. '
                                 'Please update your firmware.'.
                                 format(EX2_USB_MIN_FW, self.remote_firmware))

        # Reset the EX2 and every board on its CAN chain.
        await self.reset_controller()

        # Discover EX2, Switch and Lightshow boards on the CAN chain.
        await self.query_pkone_boards()

        await self.configure_lightshow_groups()

        # Read the initial state of all switches
        await self.read_all_switches()

        self.platform.controller_connection = self

    async def reset_controller(self):
        """Reset the controller."""
        self.platform.debug_log('Resetting controller.')

        # This command returns several responses, ending with the EX2 acknowledgement.
        self.writer.write('PRSE'.encode())
        loop = asyncio.get_running_loop()
        deadline = loop.time() + STARTUP_TIMEOUT
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise AssertionError("Timed out resetting PKONE controller")
            msg = await self._wait_for_response('PRS', 'resetting the controller', remaining)
            if msg in ('PRSE', 'PRSNE'):
                break
            if not re.fullmatch(r'PRS[0-7][XLS]E', msg):
                raise AssertionError("Unexpected PKONE reset reply: {}".format(msg))

    async def query_pkone_boards(self):
        """Ask the connected EX2 to discover the PKONE CAN chain."""
        self.platform.debug_log('Querying PKONE boards...')

        # Determine connected add-on boards (PCB command)
        # Responses:
        # EX2 - PCB0XF30H20PY = address, firmware, hardware and 48 V state
        # Switch - PCB1SF30H20I40C00PN = address, 40 inputs, outputs disabled and 48 V state
        # Lightshow - PCB2LF30H20MIX = address, firmware, hardware and RGB/RGBW capability
        # No board at the address: PCB[board number 0-7]N
        for address_id in range(8):
            self.writer.write('PCB{}E'.format(address_id).encode('ascii', 'replace'))
            msg = await self._wait_for_response('PCB', 'querying board {}'.format(address_id))
            if msg == 'PCB{}NE'.format(address_id):
                self.platform.log.debug("No board at address ID {}".format(address_id))
                continue

            switch = re.fullmatch(r'PCB([0-7])SF([0-9]+)H([0-9]+)I40C00P[YN]E', msg)
            if switch:
                if int(switch.group(1)) != address_id:
                    raise AssertionError("PKONE Switch board address mismatch")
                digits = switch.group(2)
                firmware = digits[:-1] + '.' + digits[-1]
                if version.parse(SWITCH_MIN_FW) > version.parse(firmware):
                    raise AssertionError('Firmware version mismatch. MPF requires PKONE Switch boards '
                                         'to be at least firmware {}, but yours is {}.'.format(
                                             SWITCH_MIN_FW, firmware))
                self.platform.register_switch_board(PKONESwitchBoard(address_id, firmware, switch.group(3)))
                continue

            match = re.fullmatch('PCB([0-7])([XL])F([0-9]+)H([0-9]+)(P[YN])?(RGB|RGBW|MIX)?E', msg)
            if not match:
                raise AssertionError("Invalid PKONE board reply at address {}: {}".format(address_id, msg))
            if int(match.group(1)) != address_id:
                raise AssertionError("PKONE board address mismatch: requested {}, received {}".format(address_id, msg))

            if match.group(2) == "X":
                # EX2 board. X is retained in the on-wire protocol for compatibility.
                firmware = match.group(3)[:-1] + '.' + match.group(3)[-1]
                hardware_rev = match.group(4)

                if version.parse(EX2_MIN_FW) > version.parse(firmware):
                    raise AssertionError('Firmware version mismatch. MPF requires '
                                         'PKONE EX2 boards to be at least firmware {}, but yours is {}. '
                                         'Please update your firmware.'.
                                         format(EX2_MIN_FW, firmware))

                self.platform.debug_log('PKONE EX2 Board {0}: '
                                        'Firmware: {1}, Hardware Rev: {2}'.format(address_id,
                                                                                  firmware, hardware_rev))

                self.platform.register_ex2_board(PKONEEX2Board(address_id, firmware, hardware_rev))

            elif match.group(2) == "L":
                # Lightshow board
                firmware = match.group(3)[:-1] + '.' + match.group(3)[-1]
                hardware_rev = match.group(4)
                rgbw_firmware = match.group(6) == 'RGBW'
                mixed_firmware = match.group(6) == 'MIX'

                if version.parse(LIGHTSHOW_MIN_FW) > version.parse(firmware):
                    raise AssertionError('Firmware version mismatch. MPF requires '
                                         'PKONE Lightshow boards to be at least firmware {}, but yours is {}. '
                                         'Please update your firmware.'.
                                         format(LIGHTSHOW_MIN_FW, firmware))

                self.platform.debug_log('PKONE Lightshow Board {0}: Firmware: {1} ({2}), '
                                        'Hardware Rev: {3}'.format(address_id,
                                                                   firmware,
                                                                   'MIX' if mixed_firmware else ('RGBW' if rgbw_firmware else 'RGB'),
                                                                   hardware_rev))

                self.platform.register_lightshow_board(PKONELightshowBoard(address_id,
                                                                           firmware,
                                                                           hardware_rev,
                                                                           rgbw_firmware, mixed_firmware))

            else:
                raise AttributeError("Unrecognized PKONE board type in message: {}".format(msg))

    async def configure_lightshow_groups(self):
        """Configure mixed-firmware ports before MPF creates LED channels."""
        configs = self.platform.config.get('lightshow_groups') or {}
        settings = []
        for key, value in configs.items():
            match = re.fullmatch(r'([0-3])-([1-8])', str(key))
            if not match or str(value).lower() not in ('rgb', 'rgbw'):
                raise AssertionError(f"Invalid PKONE lightshow_groups entry: {key}: {value}")
            address, group = map(int, match.groups())
            board = self.platform.pkone_lightshows.get(address)
            if board is None:
                raise AssertionError(f"No PKONE Lightshow board at address {address}")
            channels = 4 if str(value).lower() == 'rgbw' else 3
            if not board.mixed_firmware and channels != board.channels_for_group(group):
                raise AssertionError(f"Legacy Lightshow {address} cannot change RGB/RGBW type without new firmware")
            settings.append((board, group, channels))
        for board, group, channels in settings:
            if not board.mixed_firmware:
                continue
            command = f"PLT{board.addr}{group}{channels}E"
            self.writer.write(command.encode('ascii'))
            reply = await self._wait_for_response('PLT', f'configuring Lightshow {board.addr} group {group}')
            if reply != command:
                raise AssertionError(f"Unexpected PKONE LED type acknowledgement: {reply}")
            board.group_types[group] = channels

    async def read_all_switches(self):
        """Read the current state of all switches from the hardware."""
        self.platform.debug_log('Reading all switches.')
        input_boards = dict(self.platform.pkone_ex2_boards)
        input_boards.update(self.platform.pkone_switch_boards)
        for address_id, board in input_boards.items():
            self.writer.write('PSA{}E'.format(address_id).encode())
            msg = await self._wait_for_response('PSA', 'reading switches on board {}'.format(address_id))
            count = board.switch_count
            if not re.fullmatch(r'PSA' + str(address_id) + r'[01]{' + str(count) + r'}E', msg):
                raise AssertionError("Invalid PKONE switch snapshot for board {}: {}".format(address_id, msg))
            # Runtime parser strips the terminator; startup must do the same.
            self.platform.process_received_message(msg[:-1])

    def _parse_msg(self, msg):
        self.received_msg += msg

        while True:
            pos = self.received_msg.find(b'E')

            # no more complete messages
            if pos == -1:
                if len(self.received_msg) > MAX_MESSAGE_LENGTH:
                    self.received_msg = b''
                    raise AssertionError("Unterminated PKONE message exceeds {} bytes".format(MAX_MESSAGE_LENGTH))
                break
            if pos > MAX_MESSAGE_LENGTH:
                self.received_msg = b''
                raise AssertionError("PKONE message exceeds {} bytes".format(MAX_MESSAGE_LENGTH))

            msg = self.received_msg[:pos]
            self.received_msg = self.received_msg[pos + 1:]

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
