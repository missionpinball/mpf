# pylint: disable-msg=too-many-lines
"""PKONE Hardware interface.

Contains the hardware interface and drivers for the Penny K Pinball PKONE
platform hardware.
"""
import asyncio
from copy import deepcopy
from typing import Tuple, Optional

from mpf.platforms.pkone.pkone_serial_communicator import PKONESerialCommunicator
from mpf.platforms.pkone.pkone_extension import PKONEExtensionBoard
from mpf.platforms.pkone.pkone_switch import PKONESwitch, PKONESwitchNumber
from mpf.platforms.pkone.pkone_coil import PKONECoil, PKONECoilNumber
from mpf.platforms.pkone.pkone_servo import PKONEServo, PKONEServoNumber

from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig, RepulseSettings
from mpf.core.utility_functions import Util


# pylint: disable-msg=too-many-instance-attributes
class PKONEHardwarePlatform(SwitchPlatform, DriverPlatform):

    """Platform class for the PKONE Nano hardware controller.

    Args:
        machine: The MachineController instance.
    """

    __slots__ = ["config", "serial_connections", "pkone_extensions", "pkone_lightshows",
                 "_watchdog_task", "hw_switch_data", "controller_connection"]

    def __init__(self, machine) -> None:
        """Initialize PKONE platform."""
        super().__init__(machine)
        self.serial_connections = set()     # type: Set[PKONESerialCommunicator]
        self.pkone_extensions = {}          # type: Dict[int, PKONEExtensionBoard]
        self.pkone_lightshows = {}          # type: Dict[int, PKONELightshowBoard]
        self._watchdog_task = None
        self.hw_switch_data = None

        self.config = self.machine.config_validator.validate_config("pkone", self.machine.config['pkone'])
        self._configure_device_logging_and_debug("PKONE", self.config)
        self.debug_log("Configuring PKONE hardware.")

    async def initialize(self):
        """Initialize connection to PKONE Nano hardware."""
        await self._connect_to_hardware()

    def stop(self):
        """Stop platform and close connections."""
        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None

        # wait 100ms for the messages to be send
        self.machine.clock.loop.run_until_complete(asyncio.sleep(.1))

        if self.controller_connection:
            self.controller_connection.stop()
            self.controller_connection = None

        self.serial_connections = set()

    async def start(self):
        """Start listening for commands and schedule watchdog."""
        # Schedule the watchdog task to send every 500ms (the watchdog timeout on the hardware is 1 sec)
        self._watchdog_task = self.machine.clock.schedule_interval(self._update_watchdog, 500)

        for connection in self.serial_connections:
            await connection.start_read_loop()

    def _update_watchdog(self):
        """Send Watchdog command."""
        # PKONE watchdog timeout is 1 sec
        self.controller_connection.send('PWD')

    def get_info_string(self):
        """Dump infos about boards."""
        if not self.serial_connections:
            return "No connection to any Penny K Pinball PKONE controller board."

        infos = "Penny K Pinball Hardware\n"
        infos += "------------------------\n\n"
        infos += " - Connected Controllers:\n"
        for connection in sorted(self.serial_connections, key=lambda x: x.chain_serial):
            infos += "   -> PKONE Nano - Port: {} at {} baud " \
                     "(firmware v{}, hardware rev {}).\n".format(connection.port,
                                                                 connection.baud,
                                                                 connection.remote_firmware,
                                                                 connection.remove_hardware_rev)

        infos += "\n - Extension boards:\n"
        for extension in self.pkone_extensions:
            infos += "   -> Address ID: {} (firmware v{}, hardware rev {})\n".format(extension.addr,
                                                                                     extension.firmware_version,
                                                                                     extension.hardware_rev)

        infos += "\n - Lightshow boards:\n"
        for lightshow in self.pkone_lightshows:
            infos += "   -> Address ID: {} (firmware v{}, hardware rev {})\n".format(lightshow.addr,
                                                                                     lightshow.firmware_version,
                                                                                     lightshow.hardware_rev)

        return infos

    async def _connect_to_hardware(self):
        """Connect to the port in the config."""
        comm = PKONESerialCommunicator(platform=self, port=self.config['port'], baud=self.config['baud'])
        await comm.connect()
        self.serial_connections.add(comm)

    def register_extension_board(self, board):
        """Register an Extension board."""
        if board.address_id in self.pkone_extensions or board.address_id in self.pkone_lightshows:
            raise AssertionError("Duplicate address id: a board has already been "
                                 "registered at address {}".format(board.address_id))

        if board.address_id not in range(8):
            raise AssertionError("Address out of range: Extension board address id must be between 0 and 7")

        self.pkone_extensions[board.address_id] = board

    def register_lightshow_board(self, board):
        """Register a Lightshow board."""
        if board.address_id in self.pkone_extensions or board.address_id in self.pkone_lightshows:
            raise AssertionError("Duplicate address id: a board has already been "
                                 "registered at address {}".format(board.address_id))

        if board.address_id not in range(4):
            raise AssertionError("Address out of range: Lightshow board address id must be between 0 and 3")

        self.pkone_extensions[board.address_id] = board

    def _parse_coil_number(self, number: str) -> PKONECoilNumber:
        try:
            board_id_str, coil_num_str = number.split("-")
        except ValueError:
            raise AssertionError("Invalid coil number {}".format(number))

        board_id = int(board_id_str)
        coil_num = int(coil_num_str)

        if board_id not in self.pkone_extensions:
            raise AssertionError("PKONE Extension {} does not exist for coil {}".format(board_id, number))

        coil_count = self.pkone_extensions[board_id].coil_count
        if coil_count <= coil_num:
            raise AssertionError("PKONE Extension {} only has {} coils ({} - {}). Servo: {}".format(
                board_id, coil_count, 1, coil_count, number))

        return PKONECoilNumber(board_id, coil_num)

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> PKONECoil:
        """Configure a coil/driver.

        Args:
        ----
            config: Coil/driver config.
            number: Number of this coil/driver.
            platform_settings: Platform specific settings.

        Returns: Coil/driver object
        """
        # dont modify the config. make a copy
        platform_settings = deepcopy(platform_settings)

        if not self.controller_connection:
            raise AssertionError('A request was made to configure a PKONE coil, but no '
                                 'connection to a PKONE controller is available')

        if not number:
            raise AssertionError("Coil number is required")

        coil_number = self._parse_coil_number(str(number))
        return PKONECoil(config, self, coil_number, platform_settings)

    def _parse_servo_number(self, number: str) -> PKONEServoNumber:
        try:
            board_id_str, servo_num_str = number.split("-")
        except ValueError:
            raise AssertionError("Invalid servo number {}".format(number))

        board_id = int(board_id_str)
        servo_num = int(servo_num_str)

        if board_id not in self.pkone_extensions:
            raise AssertionError("PKONE Extension {} does not exist for servo {}".format(board_id, number))

        # Servos are numbered in sequence immediately after the highest coil number
        driver_count = self.pkone_extensions[board_id].coil_count
        servo_count = self.pkone_extensions[board_id].servo_count
        if servo_count <= servo_num - driver_count:
            raise AssertionError("PKONE Extension {} only has {} servos ({} - {}). Servo: {}".format(
                board_id, servo_count, driver_count + 1, driver_count + servo_count, number))

        return PKONEServoNumber(board_id, servo_num)

    async def configure_servo(self, number: str) -> PKONEServo:
        """Configure a servo.

        Args:
        ----
            number: Number of servo

        Returns: Servo object.
        """
        servo_number = self._parse_servo_number(str(number))
        return PKONEServo(servo_number, self.controller_connection)

    @classmethod
    def get_coil_config_section(cls):
        """Return coil config section."""
        return "pkone_coils"

    def _check_switch_coil_combination(self, switch, coil):
        switch_number = int(switch.hw_switch.number[0])
        coil_number = int(coil.hw_driver.number)

        switch_index = 0
        coil_index = 0
        for extension_board in self.pkone_extensions.values():
            # if switch and coil are on the same board we are fine
            if switch_index <= switch_number < switch_index + extension_board.switch_count and \
                    coil_index <= coil_number < coil_index + extension_board.coil_count:
                return
            coil_index += extension_board.coil_count
            switch_index += extension_board.switch_count

        raise AssertionError("Driver {} and switch {} are on different boards. Cannot apply rule!".format(
            coil.hw_driver.number, switch.hw_switch.number))

    def _parse_switch_number(self, number: str) -> PKONESwitchNumber:
        try:
            board_id_str, switch_num_str = number.split("-")
        except ValueError:
            raise AssertionError("Invalid switch number {}".format(number))

        board_id = int(board_id_str)
        switch_num = int(switch_num_str)

        if board_id not in self.pkone_extensions:
            raise AssertionError("PKONE Extension {} does not exist for switch {}".format(board_id, number))

        if self.pkone_extensions[board_id].switch_count <= switch_num:
            raise AssertionError("PKONE Extension {} only has {} switches. Switch: {}".format(
                board_id, self.pkone_extensions[board_id].switch_count, number))

        return PKONESwitchNumber(board_id, switch_num)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> PKONESwitch:
        """Configure the switch object for a PKONE controller.

        Args:
        ----
            number: Number of this switch.
            config: Switch config.
            platform_config: Platform specific settings.

        Returns: Switch object.
        """
        if not number:
            raise AssertionError("Switch requires a number")

        if not self.controller_connection:
            raise AssertionError("A request was made to configure a PKONE switch, but no "
                                 "connection to PKONE controller is available")

        try:
            number_tuple = self._parse_switch_number(number)
        except ValueError:
            raise AssertionError("Could not parse switch number {}/{}. Seems "
                                 "to be not a valid switch number for the"
                                 "PKONE platform.".format(config.name, number))

        self.debug_log("PKONE Switch: %s (%s)", number, config.name)

        switch_number = self._parse_switch_number(number)
        return PKONESwitch(config, switch_number, self)

    def receive_all_switches(self, msg):
        """Process the all switch states message."""
        # The PSA message contains the following information:
        # [PSA opcode] + [board address id] + 0 or 1 for each switch on the board + E
        self.debug_log("Received PSA: %s", msg)

        extension_id = int(msg[3:4])
        switch_state_array = bytearray()
        switch_state_array.extend(msg[5:-1])

        for i in range(len(switch_state_array)):
            self.hw_switch_data[(extension_id, i)] = switch_state_array[i]

    def receive_switch(self, msg):
        """Process a single switch state change."""
        # The PSW message contains the following information:
        # [PSW opcode] + [board address id] + switch number + switch state (0 or 1) + E
        self.debug_log("Received PSW: %s", msg)

        switch_number_tuple = int(msg[4]), int(msg[5:-2])
        switch_state = int(msg[-1])
        self.machine.switch_controller.process_switch_by_num(state=switch_state,
                                                             num=switch_number_tuple,
                                                             platform=self)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver."""
        raise AssertionError("Single-wound coils with EOS are not implemented in PKONE hardware.")


