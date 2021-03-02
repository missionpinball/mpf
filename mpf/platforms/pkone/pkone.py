# pylint: disable-msg=too-many-lines
"""PKONE Hardware interface.

Contains the hardware interface and drivers for the Penny K Pinball PKONE
platform hardware.
"""
import asyncio
from copy import deepcopy
from typing import Optional, Dict

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
from mpf.platforms.pkone.pkone_serial_communicator import PKONESerialCommunicator
from mpf.platforms.pkone.pkone_extension import PKONEExtensionBoard
from mpf.platforms.pkone.pkone_lightshow import PKONELightshowBoard
from mpf.platforms.pkone.pkone_switch import PKONESwitch, PKONESwitchNumber
from mpf.platforms.pkone.pkone_coil import PKONECoil, PKONECoilNumber
from mpf.platforms.pkone.pkone_servo import PKONEServo, PKONEServoNumber
from mpf.platforms.pkone.pkone_lights import PKONESimpleLED, PKONESimpleLEDNumber

from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig, RepulseSettings


# pylint: disable-msg=too-many-instance-attributes
class PKONEHardwarePlatform(SwitchPlatform, DriverPlatform):

    """Platform class for the PKONE Nano hardware controller.

    Args:
        machine: The MachineController instance.
    """

    __slots__ = ["config", "serial_connections", "pkone_extensions", "pkone_lightshows", "leds",
                 "_watchdog_task", "hw_switch_data", "controller_connection", "pkone_commands"]

    def __init__(self, machine) -> None:
        """Initialize PKONE platform."""
        super().__init__(machine)
        self.controller_connection = None
        self.serial_connections = set()     # type: Set[PKONESerialCommunicator]
        self.pkone_extensions = {}          # type: Dict[int, PKONEExtensionBoard]
        self.pkone_lightshows = {}          # type: Dict[int, PKONELightshowBoard]
        self.leds = {}
        self._watchdog_task = None
        self.hw_switch_data = None

        self.pkone_commands = {'PCN': lambda x, y: None,            # connected Nano processor
                               'PCB': lambda x, y: None,            # connected board
                               'PWD': lambda x, y: None,            # watchdog
                               'PSA': self.receive_all_switches,    # all switch states
                               'PSW': self.receive_switch,          # switch state change
                               'PXX': self.receive_error,           # error
                               }

        # Set platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['has_dmds'] = False
        self.features['has_rgb_dmds'] = False
        self.features['has_accelerometers'] = False
        self.features['has_i2c'] = False
        self.features['has_servos'] = True
        self.features['has_lights'] = True
        self.features['has_switches'] = True
        self.features['has_drivers'] = True
        self.features['max_pulse'] = 250
        self.features['tickless'] = True
        self.features['has_segment_displays'] = False
        self.features['has_hardware_sound_systems'] = False
        self.features['has_steppers'] = False
        self.features['allow_empty_numbers'] = False

        self.config = self.machine.config_validator.validate_config("pkone", self.machine.config['pkone'])
        self._configure_device_logging_and_debug("PKONE", self.config)
        self.debug_log("Configuring PKONE hardware.")

    async def initialize(self):
        """Initialize connection to PKONE Nano hardware."""
        await self._connect_to_hardware()

    def stop(self):
        """Stop platform and close connections."""
        if self.controller_connection:
            # send reset message to turn off all lights, disable all drivers
            self.controller_connection.send('PRS')

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
        self.controller_connection.send('PWDE')

    def get_info_string(self):
        """Dump infos about boards."""
        if not self.serial_connections:
            return "No connection to any Penny K Pinball PKONE controller board."

        infos = "Penny K Pinball Hardware\n"
        infos += "------------------------\n"
        infos += " - Connected Controllers:\n"
        for connection in sorted(self.serial_connections, key=lambda x: x.port):
            infos += "   -> PKONE Nano - Port: {} at {} baud " \
                     "(firmware v{}, hardware rev {}).\n".format(connection.port,
                                                                 connection.baud,
                                                                 connection.remote_firmware,
                                                                 connection.remote_hardware_rev)

        infos += "\n - Extension boards:\n"
        for extension in self.pkone_extensions.values():
            infos += "   -> Address ID: {} (firmware v{}, hardware rev {})\n".format(extension.addr,
                                                                                     extension.firmware_version,
                                                                                     extension.hardware_rev)

        infos += "\n - Lightshow boards:\n"
        for lightshow in self.pkone_lightshows.values():
            infos += "   -> Address ID: {} (firmware v{}, hardware rev {})\n".format(lightshow.addr,
                                                                                     lightshow.firmware_version,
                                                                                     lightshow.hardware_rev)

        return infos

    async def _connect_to_hardware(self):
        """Connect to the port in the config."""
        comm = PKONESerialCommunicator(platform=self, port=self.config['port'], baud=self.config['baud'])
        await comm.connect()
        self.serial_connections.add(comm)

    def register_extension_board(self, board: PKONEExtensionBoard):
        """Register an Extension board."""
        if board.addr in self.pkone_extensions or board.addr in self.pkone_lightshows:
            raise AssertionError("Duplicate address id: a board has already been "
                                 "registered at address {}".format(board.addr))

        if board.addr not in range(8):
            raise AssertionError("Address out of range: Extension board address id must be between 0 and 7")

        self.pkone_extensions[board.addr] = board

    def register_lightshow_board(self, board: PKONELightshowBoard):
        """Register a Lightshow board."""
        if board.addr in self.pkone_extensions or board.addr in self.pkone_lightshows:
            raise AssertionError("Duplicate address id: a board has already been "
                                 "registered at address {}".format(board.addr))

        if board.addr not in range(4):
            raise AssertionError("Address out of range: Lightshow board address id must be between 0 and 3")

        self.pkone_lightshows[board.addr] = board

    def process_received_message(self, msg: str):
        """Send an incoming message from the PKONE controller to the proper method for servicing.

        Args:
        ----
            msg: messaged which was received
        """
        assert self.log is not None
        cmd = msg[0:3]
        payload = msg[3:].replace('E', '')

        # Can't use try since it swallows too many errors for now
        if cmd in self.pkone_commands:
            self.pkone_commands[cmd](payload)
        else:   # pragma: no cover
            self.log.warning("Received unknown serial command %s.", msg)

    def receive_error(self, msg):
        self.log.error("Received an error message from the controller: {}".format(msg))

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
        if coil_count < coil_num or coil_num < 1:
            raise AssertionError("PKONE Extension {} only has {} coils ({} - {}). Coil: {}".format(
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

    @staticmethod
    def _check_coil_switch_combination(coil: DriverSettings, switch: SwitchSettings):
        """Checks to see if the coil/switch combination is legal for hardware rules"""

        # coil and switch must be on the same extension board (same board address id)
        if switch.hw_switch.number.board_address_id != coil.hw_driver.number.board_address_id:
            raise AssertionError("Coil {} and switch {} are on different boards. Cannot apply hardware rule!".format(
                coil.hw_driver.number, switch.hw_switch.number))

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some coil activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        Args:
        ----
            switch: The switch whose rule you want to clear.
            coil: The coil whose rule you want to clear.
        """
        self.debug_log("Clearing Hardware Rule for coil: %s, switch: %s",
                       coil.hw_driver.number, switch.hw_switch.number)
        driver = coil.hw_driver
        driver.clear_hardware_rule()

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse continues. Typically used for
        autofire coils such as pop bumpers.
        """
        self._check_coil_switch_combination(coil, enable_switch)
        driver = coil.hw_driver
        driver.set_hardware_rule(1, enable_switch, None, 0, coil.pulse_settings, None)

    def set_delayed_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings, delay_ms: int):
        """Set pulse on hit and release rule to driver.

        When a switch is hit and a certain delay passed it pulses a driver.
        When the switch is released the pulse continues.
        Typically used for kickbacks.
        """
        self._check_coil_switch_combination(coil, enable_switch)
        driver = coil.hw_driver
        driver.set_hardware_rule(2, enable_switch, None, delay_ms, coil.pulse_settings, None)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse is canceled. Typically used on
        the main coil for dual coil flippers without eos switch.
        """
        self._check_coil_switch_combination(coil, enable_switch)
        driver = coil.hw_driver
        driver.set_hardware_rule(3, enable_switch, None, 0, coil.pulse_settings, coil.hold_settings)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. Typically used for single coil flippers.
        """
        self._check_coil_switch_combination(coil, enable_switch)
        driver = coil.hw_driver
        driver.set_hardware_rule(4, enable_switch, None, 0, coil.pulse_settings, coil.hold_settings)

    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings, eos_switch: SwitchSettings,
                                                      coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. When the switch is released
        the pulse is canceled and the driver gets disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes disabled. Typically used on the main coil for dual-wound coil flippers with eos switch.
        """
        self._check_coil_switch_combination(coil, enable_switch)
        self._check_coil_switch_combination(coil, eos_switch)
        driver = coil.hw_driver
        driver.set_hardware_rule(5, enable_switch, eos_switch, 0, coil.pulse_settings, coil.hold_settings)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver becomes disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes enabled (likely with PWM).
        Typically used on the coil for single-wound coil flippers with eos switch.
        """
        raise AssertionError("Single-wound coils with EOS are not implemented in PKONE hardware.")

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

    async def get_hw_switch_states(self) -> Dict[str, bool]:
        """Return hardware states."""
        return self.hw_switch_data

    def receive_all_switches(self, msg):
        """Process the all switch states message."""
        # The PSA message contains the following information:
        # [PSA opcode] + [[board address id] + 0 or 1 for each switch on the board + X] (repeats for each
        # connected Extension board) + E
        self.debug_log("Received all switch states (PSA): %s", msg)

        hw_states = dict()

        # the message payload is delimited with an 'X' character for the switches on each board
        for board_switches in msg.split('X'):
            if len(board_switches) == 0:
                continue

            # The first character is the board address ID
            board_address_id = int(board_switches[0])
            switch_states = board_switches[1:]

            # There is one character for each switch on the board (1 = active, 0 = inactive)
            # Loop over each character and map the state to the appropriate switch number
            for index in range(len(switch_states)):
                hw_states[PKONESwitchNumber(board_address_id=board_address_id, switch_number=index + 1)] = int(
                    switch_states[index])

        self.hw_switch_data = hw_states

    def receive_switch(self, msg):
        """Process a single switch state change."""
        # The PSW message contains the following information:
        # [PSW opcode] + [board address id] + switch number + switch state (0 or 1) + E
        self.debug_log("Received switch state change (PSW): %s", msg)

        switch_number = PKONESwitchNumber(int(msg[4]), int(msg[5:-2]))
        switch_state = int(msg[-1])
        self.machine.switch_controller.process_switch_by_num(state=switch_state,
                                                             num=switch_number,
                                                             platform=self)

    def configure_light(self, number, subtype, config, platform_settings) -> LightPlatformInterface:
        """Configure light in platform."""
        del config
        if not self.controller_connection:
            raise AssertionError("A request was made to configure a PKONE switch, but no "
                                 "connection to PKONE controller is available")

        if subtype == "simple":
            return PKONESimpleLED(number, self.controller_connection.send, self.machine, self)

        if not subtype or subtype == "led":
            board_address_id, group, index  = number.split("-")
            """
            if number_str not in self.fast_leds:
                self.fast_leds[number_str] = FASTDirectLED(
                    number_str, int(self.config['hardware_led_fade_time']), self.machine)
            fast_led_channel = FASTDirectLEDChannel(self.fast_leds[number_str], channel)
            self.fast_leds[number_str].add_channel(int(channel), fast_led_channel)

            return fast_led_channel
            """
            return None

        raise AssertionError("Unknown subtype {}".format(subtype))

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light channels from number string."""
        if subtype == "simple":
            board_address_id, index = number.split('-')
            return [
                {
                    "number": "{}-{}-0".format(board_address_id, index)
                }
            ]

        if not subtype or subtype == "led":
            # if the LED number is in <board_address_id> - <group> - <channel> - <led> format, convert it to a
            # FAST hardware number
            if '-' in str(number):
                board_address_id, group, number_str, channel = str(number).split('-')
                index = 0  # TODO: implement me
            else:
                index = int(number)
            return [
                {
                    "number": "{}-{}-{}-0".format(index)
                },
                {
                    "number": "{}-{}-{}-1".format(index)
                },
                {
                    "number": "{}-{}-{}-2".format(index)
                },
            ]

        raise AssertionError("Unknown subtype {}".format(subtype))

