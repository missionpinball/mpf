# pylint: disable-msg=too-many-lines
"""PKONE Hardware interface.

Contains the hardware interface and drivers for the Penny K Pinball PKONE
platform hardware.
"""
import asyncio
from copy import deepcopy
from typing import Optional, Dict, List, Tuple, Set

from mpf.core.platform_batch_light_system import PlatformBatchLightSystem
from mpf.platforms.pkone.pkone_serial_communicator import PKONESerialCommunicator
from mpf.platforms.pkone.pkone_extension import PKONEExtensionBoard
from mpf.platforms.pkone.pkone_lightshow import PKONELightshowBoard
from mpf.platforms.pkone.pkone_switch import PKONESwitch, PKONESwitchNumber
from mpf.platforms.pkone.pkone_coil import PKONECoil, PKONECoilNumber
from mpf.platforms.pkone.pkone_servo import PKONEServo, PKONEServoNumber
from mpf.platforms.pkone.pkone_lights import PKONESimpleLED, PKONESimpleLEDNumber, PKONELEDChannel

from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig, RepulseSettings, ServoPlatform


# pylint: disable-msg=too-many-instance-attributes,too-many-public-methods
class PKONEHardwarePlatform(SwitchPlatform, DriverPlatform, LightsPlatform, ServoPlatform):

    """Platform class for the PKONE Nano hardware controller.

    Args:
    ----
        machine: The MachineController instance.
    """

    __slots__ = ["config", "serial_connections", "pkone_extensions", "pkone_lightshows", "_light_system",
                 "_watchdog_task", "hw_switch_data", "controller_connection", "pkone_commands"]

    def __init__(self, machine) -> None:
        """Initialize PKONE platform."""
        super().__init__(machine)
        self.controller_connection = None
        self.serial_connections = set()     # type: Set[PKONESerialCommunicator]
        self.pkone_extensions = {}          # type: Dict[int, PKONEExtensionBoard]
        self.pkone_lightshows = {}          # type: Dict[int, PKONELightshowBoard]
        self._light_system = None           # type: Optional[PlatformBatchLightSystem]
        self._watchdog_task = None
        self.hw_switch_data = dict()

        self.pkone_commands = {'PCN': lambda x, y: None,            # connected Nano processor
                               'PCB': lambda x, y: None,            # connected board
                               'PWD': lambda x, y: None,            # watchdog
                               'PWF': lambda x, y: None,            # watchdog stop
                               'PSA': self.receive_all_switches,    # all switch states
                               'PSW': self.receive_switch,          # switch state change
                               'PXX': self.receive_error,           # error
                               }

        # Set platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['max_pulse'] = 250
        self.features['tickless'] = True
        self.features['allow_empty_numbers'] = False

        self.config = self.machine.config_validator.validate_config("pkone", self.machine.config['pkone'])
        self._configure_device_logging_and_debug("PKONE", self.config)
        self.debug_log("Configuring PKONE hardware.")

    async def initialize(self):
        """Initialize connection to PKONE Nano hardware."""
        await self._connect_to_hardware()

        # Setup the batch light system
        self._light_system = PlatformBatchLightSystem(self.machine.clock, self._send_multiple_light_update,
                                                      self.machine.config['mpf']['default_light_hw_update_hz'],
                                                      64)

    def stop(self):
        """Stop platform and close connections."""
        if self._light_system:
            self._light_system.stop()
        if self.controller_connection:
            # send reset message to turn off all lights, disable all drivers, stop the watchdog process, etc.
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
        if self.config['watchdog']:
            # Configure the watchdog timeout interval and start it
            self.controller_connection.send('PWS{:04d}'.format(self.config['watchdog']))

            # Schedule the watchdog task to send at half the configured interval
            self._watchdog_task = self.machine.clock.schedule_interval(self._update_watchdog,
                                                                       self.config['watchdog'] / 2000)

        for connection in self.serial_connections:
            await connection.start_read_loop()

        self._initialize_led_hw_driver_alignment()
        self._light_system.start()

    def _update_watchdog(self):
        """Send Watchdog ping command."""
        self.controller_connection.send('PWD')

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
            infos += "   -> Address ID: {} ({} firmware v{}, " \
                     "hardware rev {})\n".format(lightshow.addr,
                                                 'RGBW' if lightshow.rgbw_firmware else 'RGB',
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
        """Receive an error message from the controller."""
        self.log.error("Received an error message from the controller: %s", msg)

    def _parse_coil_number(self, number: str) -> PKONECoilNumber:
        try:
            board_id_str, coil_num_str = number.split("-")
        except ValueError:
            raise AssertionError("Invalid coil number {}".format(number))

        board_id = int(board_id_str)
        coil_num = int(coil_num_str)

        if board_id not in self.pkone_extensions:
            raise AssertionError("PKONE Extension {} does not exist for coil {}".format(board_id, number))

        if coil_num == 0:
            raise AssertionError("PKONE coil numbering begins with 1. Coil: {}".format(number))

        coil_count = self.pkone_extensions[board_id].coil_count
        if coil_count < coil_num or coil_num < 1:
            raise AssertionError(
                "PKONE Extension {board_id} only has {coil_count} coils "
                "({first_coil} - {last_coil}). Coil: {number}".format(
                    board_id=board_id, coil_count=coil_count, first_coil=1, last_coil=coil_count, number=number))

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
        """Check to see if the coil/switch combination is legal for hardware rules."""
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
        del repulse_settings
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
        if servo_num <= driver_count or servo_num > driver_count + servo_count:
            raise AssertionError("PKONE Extension {} supports {} servos ({} - {}). "
                                 "Servo: {} is not a valid number.".format(
                                     board_id, servo_count, driver_count + 1, driver_count + servo_count, number))

        return PKONEServoNumber(board_id, servo_num)

    async def configure_servo(self, number: str, config: dict) -> PKONEServo:
        """Configure a servo."""
        del config
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

        if switch_num == 0:
            raise AssertionError("PKONE switch numbering begins with 1. Switch: {}".format(number))

        if self.pkone_extensions[board_id].switch_count < switch_num:
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
        del platform_config
        if not number:
            raise AssertionError("Switch requires a number")

        if not self.controller_connection:
            raise AssertionError("A request was made to configure a PKONE switch, but no "
                                 "connection to PKONE controller is available")

        try:
            switch_number = self._parse_switch_number(number)
        except ValueError:
            raise AssertionError("Could not parse switch number {}/{}. Seems "
                                 "to be not a valid switch number for the"
                                 "PKONE platform.".format(config.name, number))

        self.debug_log("PKONE Switch: %s (%s)", number, config.name)
        return PKONESwitch(config, switch_number, self)

    async def get_hw_switch_states(self) -> Dict[str, bool]:
        """Return hardware states."""
        return self.hw_switch_data

    def receive_all_switches(self, msg):
        """Process the all switch states message."""
        # The PSA message contains the following information:
        # [PSA opcode] + [[board address id] + 0 or 1 for each switch on the board] + E
        self.debug_log("Received all switch states (PSA): %s", msg)

        # the message payload is delimited with an 'X' character for the switches on each board
        # The first character is the board address ID
        board_address_id = int(msg[0])
        switch_states = msg[1:]

        # There is one character for each switch on the board (1 = active, 0 = inactive)
        # Loop over each character and map the state to the appropriate switch number
        for index, state in enumerate(switch_states):
            self.hw_switch_data[PKONESwitchNumber(board_address_id=board_address_id,
                                                  switch_number=index + 1)] = int(state)

    def receive_switch(self, msg):
        """Process a single switch state change."""
        # The PSW message contains the following information:
        # [PSW opcode] + [board address id] + switch number + switch state (0 or 1) + E
        self.debug_log("Received switch state change (PSW): %s", msg)
        switch_number = PKONESwitchNumber(int(msg[0]), int(msg[1:3]))
        switch_state = int(msg[-1])
        self.machine.switch_controller.process_switch_by_num(state=switch_state,
                                                             num=switch_number,
                                                             platform=self)

    # pylint: disable-msg=too-many-locals
    async def _send_multiple_light_update(self, sequential_brightness_list: List[Tuple[PKONELEDChannel,
                                                                                       float, int]]):
        # determine how many channels are to be updated and the common fade time
        first_channel, _, common_fade_ms = sequential_brightness_list[0]
        start_index = first_channel.index

        # get the lightshow board that will be sent the command (need to know if rgb or rgbw board)
        lightshow = self.pkone_lightshows[first_channel.board_address_id]
        if lightshow.rgbw_firmware:
            cmd_opcode = "PWB"
            channel_grouping = 4
        else:
            cmd_opcode = "PLB"
            channel_grouping = 3

        # determine if first and last batch channels are properly aligned to internal LED boundaries
        first_channel_alignment_offset = first_channel.index % channel_grouping
        last_channel_alignment_offset = (first_channel.index + len(sequential_brightness_list)) % channel_grouping

        # Note: software fading will automatically be used when batch channels
        # are not aligned to hardware LED boundaries

        if first_channel_alignment_offset > 0:
            # the first channel does not align with internal hardware boundary, need to retrieve other
            # channels for the first light
            current_time = self._light_system.clock.get_time()
            channel = first_channel
            previous_channel = None
            for _ in range(first_channel_alignment_offset):
                if channel:
                    previous_channel = lightshow.get_channel_hw_driver(first_channel.group,
                                                                       channel.get_predecessor_number())
                if previous_channel:
                    brightness, fade_ms, _ = previous_channel.get_fade_and_brightness(current_time)
                    channel = previous_channel
                else:
                    brightness = 0.0
                    fade_ms = 0
                    channel = None

                sequential_brightness_list.insert(0, (channel, brightness, fade_ms))
                start_index = start_index - 1

        if last_channel_alignment_offset > 0:
            current_time = self._light_system.clock.get_time()
            channel = sequential_brightness_list[-1][0]
            next_channel = None
            for _ in range(channel_grouping - last_channel_alignment_offset):
                if channel:
                    next_channel = lightshow.get_channel_hw_driver(first_channel.group,
                                                                   channel.get_successor_number())
                if next_channel:
                    brightness, fade_ms, _ = next_channel.get_fade_and_brightness(current_time)
                    channel = next_channel
                else:
                    brightness = 0.0
                    fade_ms = 0
                    channel = None

                sequential_brightness_list.append((channel, brightness, fade_ms))

        assert start_index % channel_grouping == 0
        assert len(sequential_brightness_list) % channel_grouping == 0

        # generate batch update command using brightness values (3 digit int values)
        # Note: fade time is in 10ms units
        cmd = "{}{}{}{:02d}{:02d}{:04d}{}".format(cmd_opcode,
                                                  first_channel.board_address_id,
                                                  first_channel.group,
                                                  start_index // channel_grouping + 1,
                                                  len(sequential_brightness_list) // channel_grouping,
                                                  int(common_fade_ms / 10),
                                                  "".join("%03d" % (b[1] * 255) for b in sequential_brightness_list))
        self.controller_connection.send(cmd)

    def configure_light(self, number, subtype, config, platform_settings):
        """Configure light in platform."""
        del platform_settings

        if not self.controller_connection:
            raise AssertionError("A request was made to configure a PKONE light, but no "
                                 "connection to PKONE controller is available")

        if subtype == "simple":
            # simple LEDs use the format <board_address_id> - <led> (simple LEDs only have 1 channel)
            board_address_id, index = number.split('-')
            return PKONESimpleLED(PKONESimpleLEDNumber(int(board_address_id), int(index)),
                                  self.controller_connection.send, self)

        if not subtype or subtype == "led":
            board_address_id, group, index = number.split("-")
            led_channel = PKONELEDChannel(board_address_id, group, index, config, self._light_system)
            lightshow = self.pkone_lightshows[int(board_address_id)]
            lightshow.add_channel_hw_driver(int(group), led_channel)
            self._light_system.mark_dirty(led_channel)
            return led_channel

        raise AssertionError("Unknown subtype {}".format(subtype))

    def _led_is_hardware_aligned(self, led_name) -> bool:
        """Determine whether the specified LED is hardware aligned."""
        light = self.machine.lights[led_name]
        hw_numbers = light.get_hw_numbers()
        board_address_id, _, index = hw_numbers[0].split("-")
        lightshow = self.pkone_lightshows[int(board_address_id)]
        if lightshow.rgbw_firmware:
            channel_grouping = 4
        else:
            channel_grouping = 3
        if len(hw_numbers) != channel_grouping:
            return False
        return int(index) % channel_grouping == 0

    def _initialize_led_hw_driver_alignment(self):
        """Set hardware aligned flag for all led hardware driver channels."""
        for _, lightshow in self.pkone_lightshows.items():
            for channel in lightshow.get_all_channel_hw_drivers():
                channel.set_hardware_aligned(self._led_is_hardware_aligned(channel.config.name))

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light channels from number string."""
        if subtype == "simple":
            # simple LEDs use the format <board_address_id> - <led> (simple LEDs only have 1 channel)
            board_address_id, index = number.split('-')
            return [
                {
                    "number": "{}-{}".format(board_address_id, index)
                }
            ]

        if not subtype or subtype == "led":
            # Normal LED number format: <board_address_id> - <group> - <led>
            board_address_id, group, number_str = str(number).split('-')
            index = int(number_str)

            # Determine if there are 3 or 4 channels depending upon firmware on board
            if self.pkone_lightshows[board_address_id].rgbw_firmware:
                # rgbw uses 4 channels per led
                return [
                    {
                        "number": "{}-{}-{}".format(board_address_id, group, (index - 1) * 4)
                    },
                    {
                        "number": "{}-{}-{}".format(board_address_id, group, (index - 1) * 4 + 1)
                    },
                    {
                        "number": "{}-{}-{}".format(board_address_id, group, (index - 1) * 4 + 2)
                    },
                    {
                        "number": "{}-{}-{}".format(board_address_id, group, (index - 1) * 4 + 3)
                    },
                ]

            # rgb uses 3 channels per led
            return [
                {
                    "number": "{}-{}-{}".format(board_address_id, group, (index - 1) * 3)
                },
                {
                    "number": "{}-{}-{}".format(board_address_id, group, (index - 1) * 3 + 1)
                },
                {
                    "number": "{}-{}-{}".format(board_address_id, group, (index - 1) * 3 + 2)
                },
            ]

        raise AssertionError("Unknown light subtype {}".format(subtype))
