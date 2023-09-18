"""Contains the drivers and interface code for pinball machines which use the Multimorphic P3-ROC hardware controllers.

Much of this code is from the P-ROC drivers section of the pyprocgame project,
written by Adam Preble and Gerry Stellenberg. It was originally released under
the MIT license and is released here under the MIT License.

More info on the P3-ROC hardware platform: http://pinballcontrollers.com/

Original code source on which this module was based:
https://github.com/preble/pyprocgame
"""
import asyncio
import logging

from typing import Dict, List, Optional  # pylint: disable-msg=cyclic-import,unused-import

from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.platforms.interfaces.i2c_platform_interface import I2cPlatformInterface

from mpf.core.platform import I2cPlatform, AccelerometerPlatform, DriverConfig, SwitchConfig
from mpf.platforms.interfaces.accelerometer_platform_interface import AccelerometerPlatformInterface
from mpf.platforms.p_roc_common import PDBConfig, PROCBasePlatform
from mpf.platforms.p_roc_devices import PROCDriver

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.accelerometer import Accelerometer     # pylint: disable-msg=cyclic-import,unused-import

WRITE_DATA_FORMAT = "Setting 0x02 %s to %s"


class P3RocGpioSwitch(SwitchPlatformInterface):

    """P3-ROC switch on GPIOs."""

    __slots__ = ["index"]

    def __init__(self, config, number, index, platform):
        """initialize P-ROC switch."""
        super().__init__(config, number, platform)
        self.index = index

    def get_board_name(self):
        """Return board of the GPIOs."""
        return "P3-Roc GPIOs"

    @property
    def has_rules(self):
        """Return false as we do not support rules."""
        return False


class P3RocGpioDriver(DriverPlatformInterface):

    """P3-Roc driver in GPIOs."""

    __slots__ = ["index", "platform"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, number, config, index, platform):
        """initialize driver."""
        super().__init__(config, number)
        self.index = index
        self.platform = platform

    def get_board_name(self):
        """Return board of the GPIOs."""
        return "P3-Roc GPIOs"

    def disable(self):
        """Disable (turn off) this GPIO."""
        self.platform.set_gpio(self.index, False)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this GPIO."""
        if pulse_settings.power != 1 or hold_settings.power != 1:
            raise AssertionError("pulse_power and hold_power both must be 1.0 for GPIO drivers. Let us know in the "
                                 "forum if you need this.")

        self.platform.set_gpio(self.index, True)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse GPIO."""
        raise AssertionError("Not currently implemented. Let us know in the forum if you need pulses on GPIOs.")

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise AssertionError("Not currently implemented. Let us know in the forum if you need timed_enable on GPIOs.")

    @property
    def has_rules(self):
        """Return false as we do not support rules."""
        return False


class P3RocHardwarePlatform(PROCBasePlatform, I2cPlatform, AccelerometerPlatform):

    """Platform class for the P3-ROC hardware controller.

    Args:
    ----
        machine: The MachineController instance.
    """

    __slots__ = ["_burst_opto_drivers_to_switch_map", "_burst_switches", "_bursts_enabled", "acceleration",
                 "accelerometer_device", "gpio_poll_task", "gpio_config"]

    def __init__(self, machine):
        """initialize and connect P3-Roc."""
        super().__init__(machine)
        # validate config for p3_roc
        self.config = self.machine.config_validator.validate_config("p3_roc", self.machine.config.get('p_roc', {}))
        self._configure_device_logging_and_debug('P-Roc', self.config)

        if self.config['driverboards']:
            self.machine_type = self.pinproc.normalize_machine_type(self.config['driverboards'])
        else:
            self.machine_type = self.pinproc.normalize_machine_type(self.machine.config['hardware']['driverboards'])

        self.debug = self.config["debug"]

        if self.machine_type != self.pinproc.MachineTypePDB:
            raise AssertionError("P3-Roc can only handle PDB driver boards")

        # Because PDBs can be configured in many different ways, we need to
        # traverse the YAML settings to see how many PDBs are being used.
        # Then we can configure the P3-ROC appropriately to use those PDBs.
        # Only then can we relate the YAML coil/light #'s to P3-ROC numbers for
        # the collections.

        self.debug_log("Configuring P3-ROC for PDB driver boards.")
        self._burst_opto_drivers_to_switch_map = {}
        self._burst_switches = []   # type: List[P3RocBurstOpto]
        self._bursts_enabled = False
        self.gpio_poll_task = None
        self.gpio_config = 0

        self.acceleration = [0] * 3
        self.accelerometer_device = None    # type: Optional[PROCAccelerometer]

    async def connect(self):
        """Connect to the P3-Roc."""
        await super().connect()

        self.pdbconfig = PDBConfig(self, self.machine.config, self.pinproc.DriverCount)

        if self.dipswitches & 0x01:
            self.log.info("Burst drivers are configured as outputs (DIP Switch 1 set). "
                          "You cannot use IDs 0-3 for PD-16/PD-LED boards.")

            if self.version < 2 or self.revision < 6:
                raise AssertionError("Local inputs are supported only in FW 2.6+. Disable DIP 1 or update firmware.")

        if self.dipswitches & 0x02:
            self.log.info("Burst switches are configured as inputs (DIP Switch 2 set). "
                          "You cannot use IDs 0-3 for SW-16 boards.")

            if self.version < 2 or self.revision < 6:
                raise AssertionError("Local inputs are supported only in FW 2.6+. Disable DIP 2 or update firmware.")

            for board in range(0, 4):
                device_type = await self.run_proc_cmd("read_data", 2, (1 << 12) + (board << 6))
                if device_type != 0:
                    raise AssertionError("Invalid P3-Roc configuration. Found SW-16 with ID {} which is invalid "
                                         "because burst switches/drivers which are configured as inputs/outputs use "
                                         "the same switch position. Either disabled DIP 2 or assign ID >= 4 to "
                                         "all your SW-16s.")

        # remove all burst ir mappings
        for driver in range(0, 64):
            self.run_proc_cmd_no_wait("write_data", 0x02, 0x80 + (driver * 2), 0)
            self.run_proc_cmd_no_wait("write_data", 0x02, 0x81 + (driver * 2), 0)

        # disable burst IRs
        burst_config1 = 0
        self.run_proc_cmd_no_wait("write_data", 0x02, 0x01, burst_config1)

    async def start(self):
        """Start GPIO poller."""
        await super().start()
        if self.config["gpio_map"]:
            has_inputs = False
            for gpio_index, state in self.config["gpio_map"].items():
                if state == "output":
                    self.gpio_config += 1 << (gpio_index + 8)
                else:
                    has_inputs = True

            if has_inputs:
                self.gpio_poll_task = asyncio.create_task(self._poll_gpios())
                self.gpio_poll_task.add_done_callback(Util.raise_exceptions)

            self.run_proc_cmd_no_wait("write_data", 0x00, 0x03, self.gpio_config)

    async def _poll_gpios(self):
        """Poll GPIOs."""
        poll_sleep = 1 / self.config["gpio_poll_frequency"]
        gpio_state_old = None
        while True:
            await asyncio.sleep(poll_sleep)
            gpio_state = await self.run_proc_cmd("read_data", 0x00, 0x04)
            for gpio_index, state in self.config["gpio_map"].items():
                if state == "input" and (gpio_state_old is None or (gpio_state ^ gpio_state_old) & (1 << gpio_index)):
                    self.machine.switch_controller.process_switch_by_num("gpio-{}".format(gpio_index),
                                                                         bool(gpio_state & (1 << gpio_index)), self)
            gpio_state_old = gpio_state

    def set_gpio(self, index, state):
        """Set GPIO state."""
        new_gpio_config = self.gpio_config
        if state:
            new_gpio_config |= 1 << index
        else:
            new_gpio_config &= 0xffff ^ (1 << index)

        if new_gpio_config != self.gpio_config:
            self.gpio_config = new_gpio_config
            self.run_proc_cmd_no_wait("write_data", 0x00, 0x03, self.gpio_config)

    def stop(self):
        """Stop platform."""
        super().stop()
        if self.gpio_poll_task:
            self.gpio_poll_task.cancel()
            self.gpio_poll_task = None

    def _get_default_subtype(self):
        """Return default subtype for P3-Roc."""
        return "led"

    def __repr__(self):
        """Return string representation."""
        return '<Platform.P3-ROC>'

    async def configure_i2c(self, number: str):
        """Configure I2C device on P3-Roc."""
        return P3RocI2c(number, self)

    @classmethod
    def scale_accelerometer_to_g(cls, raw_value):
        """Convert internal representation to g."""
        # raw value is 0 to 16384 -> 14 bit
        # scale is -2g to 2g (2 complement)
        if raw_value & (1 << 13):
            raw_value -= 1 << 14

        g_value = float(raw_value) / (1 << 12)

        return g_value

    def configure_accelerometer(self, number, config, callback):
        """Configure the accelerometer on the P3-ROC."""
        del config
        if number != "1":
            raise AssertionError("P3-ROC only has one accelerometer. Use number 1. Found: {}".format(number))

        self.accelerometer_device = PROCAccelerometer(callback)
        self._configure_accelerometer()

        return self.accelerometer_device

    def _configure_accelerometer(self):

        # enable polling every 128ms
        enable = 0x0F

        # configure some P3-Roc registers

        self.run_proc_cmd_no_wait("write_data", 6, 0x000, enable)

        # CTRL_REG1 - set to standby
        self.run_proc_cmd_no_wait("write_data", 6, 0x12A, 0)

        # XYZ_DATA_CFG - disable high pass filter, scale 0 to 2g
        self.run_proc_cmd_no_wait("write_data", 6, 0x10E, 0x00)

        # CTRL_REG1 - set device to active and in low noise mode
        # 800HZ output data rate
        self.run_proc_cmd_no_wait("write_data", 6, 0x12A, 0x05)

        # CTRL_REG2 - set no sleep, high resolution mode
        self.run_proc_cmd_no_wait("write_data", 6, 0x12B, 0x02)

        # for auto-polling of accelerometer every 128 ms (8 times a sec). set 0x0F
        # disable polling + IRQ status addr FF_MT_SRC
        self.run_proc_cmd_no_wait("write_data", 6, 0x000, 0x1E0F)
        # flush data to proc
        self.run_proc_cmd_no_wait("flush")

    def get_info_string(self):
        """Dump infos about boards."""
        infos = "Firmware Version: {} Firmware Revision: {} Hardware Board ID: {}\n".format(
            self.version, self.revision, self.hardware_version)

        infos += "SW-16 boards found:\n"

        for board in range(0, 32):
            device_type = self.run_proc_cmd_sync("read_data", 2, (1 << 12) + (board << 6))
            board_id = self.run_proc_cmd_sync("read_data", 2, (1 << 12) + (board << 6) + 1)
            if device_type != 0:
                infos += " - Board: {} Switches: 16 Device Type: {:X} Board ID: {:X}\n".format(
                    board, device_type, board_id)

        return infos

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Create a P3-ROC driver.

        Typically drivers are coils or flashers, but for the P3-ROC this is
        also used for matrix-based lights.

        Args:
        ----
            config: Dictionary of settings for the driver.
            number: Number of this driver.
            platform_settings: Platform specific settings

        Returns a reference to the PROCDriver object which is the actual object you
        can use to pulse(), patter(), enable(), etc.
        """
        # todo need to add virtual driver support for driver counts > 256

        # Find the P3-ROC number for each driver. For P3-ROC driver boards, the
        # P3-ROC number is specified via the Ax-By-C format.

        if number.startswith("direct-"):
            return self._configure_direct_driver(config, number)
        if number.startswith("gpio-"):
            return self._configure_gpio_driver(config, number)

        proc_num = self.pdbconfig.get_proc_coil_number(str(number))
        if proc_num == -1:
            raise AssertionError("Driver {} cannot be controlled by the P3-ROC. ".format(str(number)))

        if proc_num < 32 and self.dipswitches & 0x01:
            raise AssertionError("Cannot use PD-16 with ID 0 or 1 when DIP 1 is on the P3-Roc. Turn DIP 1 off or "
                                 "renumber PD-16s. Driver: {}".format(number))

        proc_driver_object = PROCDriver(proc_num, config, self, number, True)

        return proc_driver_object

    def _configure_direct_driver(self, config, number):
        try:
            _, driver_number = number.split("-", 2)
            driver_number = int(driver_number)
        except (ValueError, TypeError):
            raise AssertionError("Except format direct-X with 0 <= X <= 63. Invalid format. Got: {}".format(number))

        if 0 < driver_number > 63:
            raise AssertionError("Except format direct-X with 0 <= X <= 63. X out of bounds. Got: {}".format(number))

        if not self.dipswitches & 0x01:
            raise AssertionError("Set DIP 1 on the P3-Roc to use burst switches as local outputs")

        return PROCDriver(driver_number, config, self, number, True)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict):
        """Configure a P3-ROC switch.

        Args:
        ----
            number: Number of this switch
            config: Dictionary of settings for the switch.
            platform_config: Platform specific settings.

        Returns: A configured switch object.
        """
        del platform_config
        if number.startswith("burst-"):
            return self._configure_burst_opto(config, number)
        if number.startswith("direct-"):
            return self._configure_direct_switch(config, number)
        if number.startswith("gpio-"):
            return self._configure_gpio_switch(config, number)

        proc_num = self.pdbconfig.get_proc_switch_number(str(number))
        if 0 <= proc_num < 64 and self.dipswitches & 0x02:
            raise AssertionError("Cannot use SW-16 with ID 0-3 when DIP 2 is on the P3-Roc. Turn DIP 2 off or "
                                 "renumber SW-16s. Switch: {}".format(number))
        return self._configure_switch(config, proc_num)

    def _configure_gpio_switch(self, config, number):
        _, switch_number_str = number.split("-", 2)
        index = int(switch_number_str)

        if self.config["gpio_map"].get(index, None) != "input":
            self.raise_config_error("GPIO {} is not configured as input in gpio_map.".format(number), 1)

        return P3RocGpioSwitch(config, number, index, self)

    def _configure_gpio_driver(self, config, number):
        _, driver_number_str = number.split("-", 2)
        index = int(driver_number_str)

        if self.config["gpio_map"].get(index, None) != "output":
            self.raise_config_error("GPIO {} is not configured as output in gpio_map.".format(number), 2)

        return P3RocGpioDriver(config, number, index, self)

    def _configure_direct_switch(self, config, number):
        try:
            _, switch_number = number.split("-", 2)
            switch_number = int(switch_number)
        except (ValueError, TypeError):
            raise AssertionError("Except format direct-X with 0 <= X <= 63. Invalid format. Got: {}".format(number))

        if 0 < switch_number > 63:
            raise AssertionError("Except format direct-X with 0 <= X <= 63. X out of bounds. Got: {}".format(number))

        if not self.dipswitches & 0x02:
            raise AssertionError("Set DIP 2 on the P3-Roc to use burst switches as local inputs")

        return self._configure_switch(config, switch_number)

    # pylint: disable-msg=too-many-locals
    def _configure_burst_opto(self, config, number):
        """Configure burst opto on the P3-Roc.

        From Gerry:
        Iterate txIndex from 0 to 63 and fill in the rxMap for each.
        The rx map can overlap. Doesn't matter. The P3-ROC hardware drives burst tx0 then checks the 5 mapped rx.
        Then it drives burst tx1 and checks its 5 mapped rx. Etc up to tx63.
        Also be sure to set the Max burst tx in Switch Controller Burst Configuration 1 register (as documented in the
        programmer's reference).
        Only other thing I can think that matters is this. There are 64 burst tx (outputs) on the board, but only 32
        actual drivers in the code. 0:31 are duplicated as 32:63. So at any one time, 2 tx pins are active.

        Now for burst rx map configuration:
        // Program Count into 1st address for transmitter
        data = (uint)rx_list.Count;
        Machine.PROC.write_data (switchModule, (uint)(burstConfigOffset + tx*2), data);

        // Prepare rx map
        data = 0;
        foreach (int receiver in rx_list) {
          data = (data << 6) | ((uint)receiver & 0x3f);
        }
        Machine.PROC.write_data (switchModule, (uint)(burstConfigOffset + tx*2+1), data);
        """
        # parse input and driver switches first
        try:
            _, input_switch, driver = number.split("-", 3)
            input_switch = int(input_switch)
            driver = int(driver)
        except ValueError:
            raise AssertionError("Burst Opto {} is invalid. Format should be burst-XX-YY with X=input Y=driver.")

        # verify we are not conflicting with local inputs
        if self.dipswitches & 0x03:
            raise AssertionError("Cannot use Burst Optos when local inputs or outputs are used. Disable DIP 1 and 2 "
                                 "on the P3-Roc.")

        # enable burst IRs
        if not self._bursts_enabled:
            self._bursts_enabled = True
            self.log.info("Enabling all burst opto on the P3-Roc.")
            burst_config0 = self.config['burst_us_per_half_pulse'] & 0x3F
            burst_config0 |= (self.config['burst_number_of_pulses_to_drive_output'] & 0x1F) << 6
            burst_config0 |= (self.config['burst_number_of_idle_pulses_before_next'] & 0x3F) << 12
            burst_config0 |= (self.config['burst_number_of_burst_pulses_before_check'] & 0x3F) << 18
            burst_config0 |= ((self.config['burst_ms_between_scans'] - 1) & 0x1F) << 24
            self.run_proc_cmd_no_wait("write_data", 0x02, 0x00, burst_config0)
            self.debug_log("Setting 0x02 0x00 to %s", burst_config0)

            burst_config1 = (1 << 31) | 0x1F

            self.run_proc_cmd_no_wait("write_data", 0x02, 0x01, burst_config1)
            self.debug_log("Setting 0x02 0x01 to %s", burst_config1)

            # enable receiver 63 for all of the optos (works around bug in fpga)
            for driver_num in range(0, 64):
                self.run_proc_cmd_no_wait("write_data", 0x02, 0x80 + (driver_num * 2), 1)
                self.debug_log(WRITE_DATA_FORMAT, 0x80 + (driver_num * 2), 1)
                self.run_proc_cmd_no_wait("write_data", 0x02, 0x81 + (driver_num * 2), 63)
                self.debug_log(WRITE_DATA_FORMAT, 0x81 + (driver_num * 2), 63)

        # configure driver for receiver
        if driver not in self._burst_opto_drivers_to_switch_map:
            self._burst_opto_drivers_to_switch_map[driver] = []

        if input_switch in self._burst_opto_drivers_to_switch_map[driver]:
            raise AssertionError("Input {} already configured for driver {} in {}. Make sure to configure each "
                                 "burst input<->driver combination only once.".format(input_switch, driver, number))

        # tell p3-roc to check this input for that driver
        self._burst_opto_drivers_to_switch_map[driver].append(input_switch)

        if len(self._burst_opto_drivers_to_switch_map[driver]) > 5:
            raise AssertionError("Every burst driver only supports up to 5 drivers. Driver {} exceeded that with "
                                 "switch {}.".format(driver, number))

        rx_to_check_for_this_transmitter = 0
        for switch in self._burst_opto_drivers_to_switch_map[driver]:
            rx_to_check_for_this_transmitter <<= 6
            rx_to_check_for_this_transmitter += switch

        addr_80 = 0x80 + (driver * 2)
        data_80 = len(self._burst_opto_drivers_to_switch_map[driver])
        self.debug_log(WRITE_DATA_FORMAT, addr_80, data_80)
        self.run_proc_cmd_no_wait("write_data", 0x02, addr_80, data_80)

        addr_81 = 0x81 + (driver * 2)
        self.debug_log(WRITE_DATA_FORMAT, addr_81, rx_to_check_for_this_transmitter)
        self.run_proc_cmd_no_wait("write_data", 0x02, addr_81, rx_to_check_for_this_transmitter)

        burst_switch = P3RocBurstOpto(config, number, input_switch, driver, self)
        self._burst_switches.append(burst_switch)

        return burst_switch

    async def get_hw_switch_states(self) -> Dict[str, bool]:
        """Read in and set the initial switch state.

        The P-ROC uses the following values for hw switch states:
        1 - closed (debounced)
        2 - open (debounced)
        3 - closed (not debounced)
        4 - open (not debounced)
        """
        states = await self.run_proc_cmd("switch_get_states")
        result = {}     # type: Dict[str, bool]

        for switch, state in enumerate(states):
            # Note: The P3-ROC will return a state of "3" for switches from non-
            # connected SW-16 boards, so that's why we only check for "1" below
            result[switch] = bool(state == 1)

        # assume 0 for all bursts initially
        for burst_switch in self._burst_switches:
            result[burst_switch.number] = False

        # read GPIOs
        if self.config["gpio_map"]:
            gpio_state = await self.run_proc_cmd("read_data", 0x00, 0x04)
            for gpio_index, state in self.config["gpio_map"].items():
                if state == "input":
                    result["gpio-{}".format(gpio_index)] = bool(gpio_state & (1 << gpio_index))

        return result

    def process_events(self, events):
        """Process events from the P3-Roc."""
        for event in events:
            event_type = event['type']
            event_value = event['value']
            if event_type in (self.pinproc.EventTypeSwitchClosedDebounced,
                              self.pinproc.EventTypeSwitchClosedNondebounced):
                self.machine.switch_controller.process_switch_by_num(
                    state=1, num=event_value, platform=self)
            elif event_type in (self.pinproc.EventTypeSwitchOpenDebounced,
                                self.pinproc.EventTypeSwitchOpenNondebounced):
                self.machine.switch_controller.process_switch_by_num(
                    state=0, num=event_value, platform=self)

            # The P3-ROC will always send all three values sequentially.
            # Therefore, we will trigger after the Z value
            elif event_type == self.pinproc.EventTypeAccelerometerX:
                self.acceleration[0] = event_value
                if self.debug:
                    self.debug_log("Got Accelerometer value X. Value: %s", event_value)
            elif event_type == self.pinproc.EventTypeAccelerometerY:
                self.acceleration[1] = event_value
                if self.debug:
                    self.debug_log("Got Accelerometer value Y. Value: %s", event_value)
            elif event_type == self.pinproc.EventTypeAccelerometerZ:
                self.acceleration[2] = event_value

                # trigger here
                if self.accelerometer_device:
                    self.accelerometer_device.update_acceleration(
                        self.scale_accelerometer_to_g(self.acceleration[0]),
                        self.scale_accelerometer_to_g(self.acceleration[1]),
                        self.scale_accelerometer_to_g(self.acceleration[2]))
                if self.debug:
                    self.debug_log("Got Accelerometer value Z. Value: %s", event_value)
            elif event_type == self.pinproc.EventTypeBurstSwitchOpen:
                if self.debug:
                    self.debug_log("Got burst open event value %s", event_value)
                self._handle_burst(event_value, 0)
            elif event_type == self.pinproc.EventTypeBurstSwitchClosed:
                if self.debug:
                    self.debug_log("Got burst closed event value %s", event_value)
                self._handle_burst(event_value, 1)
            else:   # pragma: no cover
                self.log.warning("Received unrecognized event from the P3-ROC. "
                                 "Type: %s, Value: %s", event_type, event_value)

    def _handle_burst(self, event_value, state):
        input_num = event_value & 0x3F
        output_num = (event_value >> 6) & 0x1F
        burst_number1 = "burst-{}-{}".format(input_num, output_num)
        self.machine.switch_controller.process_switch_by_num(state=state,
                                                             num=burst_number1,
                                                             platform=self)
        burst_number2 = "burst-{}-{}".format(input_num, output_num + 32)
        self.machine.switch_controller.process_switch_by_num(state=state,
                                                             num=burst_number2,
                                                             platform=self)


class P3RocI2c(I2cPlatformInterface):

    """I2c device on a P3-Roc."""

    __slots__ = ["platform", "address", "proc"]

    def __init__(self, number: str, platform) -> None:
        """initialize I2c device on P3_Roc."""
        super().__init__(number)
        self.platform = platform
        self.address = number

    def i2c_write8(self, register, value):
        """Write an 8-bit value to the I2C bus of the P3-Roc."""
        self.platform.run_proc_cmd_no_wait("write_data", 7, int(self.address) << 9 | register, value)

    async def i2c_read8(self, register):
        """Read an 8-bit value from the I2C bus of the P3-Roc."""
        data = await self.platform.run_proc_cmd("read_data", 7, int(self.address) << 9 | register)
        return data & 0xFF

    async def i2c_read_block(self, register, count):
        """Read block via I2C."""
        result = []
        position = 0
        while position < count:
            if count - position == 1:
                data = await self.i2c_read8(register + position)
                result.append(data)
                position += 1
            else:
                data = await self.i2c_read16(register)
                result.append((data >> 8) & 0xFF)
                result.append(data & 0xFF)
                position += 2
        return result

    async def i2c_read16(self, register) -> int:
        """Read an 16-bit value from the I2C bus of the P3-Roc."""
        return self.platform.run_proc_cmd("read_data", 7, int(self.address) << 9 | 1 << 8 | register)


class PROCAccelerometer(AccelerometerPlatformInterface):

    """The accelerometer on the P3-Roc."""

    __slots__ = ["callback"]

    def __init__(self, callback: "Accelerometer") -> None:
        """Remember the callback."""
        self.callback = callback    # type: Accelerometer

    def update_acceleration(self, x: float, y: float, z: float) -> None:
        """Call the callback."""
        self.callback.update_acceleration(x, y, z)


class P3RocBurstOpto(SwitchPlatformInterface):

    """A burst opto switch/driver combination."""

    __slots__ = ["input_switch", "driver", "log"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, config, number, input_switch, driver, platform):
        """initialize burst opto."""
        super().__init__(config, number, platform)
        self.input_switch = input_switch
        self.driver = driver
        self.log = logging.getLogger('P3RocBurstOpto')

    def get_board_name(self):
        """Return board of the switch."""
        return "P3-Roc Burst Opto Input {} Driver {}".format(self.input_switch, self.driver)
