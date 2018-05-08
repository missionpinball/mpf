"""Contains the drivers and interface code for pinball machines which use the Multimorphic P3-ROC hardware controllers.

Much of this code is from the P-ROC drivers section of the pyprocgame project,
written by Adam Preble and Gerry Stellenberg. It was originally released under
the MIT license and is released here under the MIT License.

More info on the P3-ROC hardware platform: http://pinballcontrollers.com/

Original code source on which this module was based:
https://github.com/preble/pyprocgame
"""

import logging
import asyncio

from mpf.core.platform import I2cPlatform, AccelerometerPlatform, DriverConfig, SwitchConfig
from mpf.platforms.interfaces.accelerometer_platform_interface import AccelerometerPlatformInterface
from mpf.platforms.p_roc_common import PDBConfig, PROCBasePlatform
from mpf.platforms.p_roc_devices import PROCDriver

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.accelerometer import Accelerometer


class P3RocHardwarePlatform(PROCBasePlatform, I2cPlatform, AccelerometerPlatform):

    """Platform class for the P3-ROC hardware controller.

    Args:
        machine: The MachineController instance.

    Attributes:
        machine: The MachineController instance.
    """

    def __init__(self, machine):
        """Initialise and connect P3-Roc."""
        super().__init__(machine)
        self.log = logging.getLogger('P3-ROC')
        self.debug_log("Configuring P3-ROC hardware.")

        # validate config for p3_roc
        self.config = self.machine.config_validator.validate_config("p3_roc", self.machine.config['p_roc'])

        if self.machine_type != self.pinproc.MachineTypePDB:
            raise AssertionError("P3-Roc can only handle PDB driver boards")

        self.connect()

        # Because PDBs can be configured in many different ways, we need to
        # traverse the YAML settings to see how many PDBs are being used.
        # Then we can configure the P3-ROC appropriately to use those PDBs.
        # Only then can we relate the YAML coil/light #'s to P3-ROC numbers for
        # the collections.

        self.debug_log("Configuring P3-ROC for PDB driver boards.")
        self.pdbconfig = PDBConfig(self.proc, self.machine.config, self.pinproc.DriverCount)

        self.acceleration = [0] * 3
        self.accelerometer_device = None    # type: PROCAccelerometer

    def _get_default_subtype(self):
        """Return default subtype for P3-Roc."""
        return "led"

    def __repr__(self):
        """Return string representation."""
        return '<Platform.P3-ROC>'

    def i2c_write8(self, address, register, value):
        """Write an 8-bit value to the I2C bus of the P3-Roc."""
        self.proc.write_data(7, int(address) << 9 | register, value)

    @asyncio.coroutine
    def i2c_read8(self, address, register):
        """Read an 8-bit value from the I2C bus of the P3-Roc."""
        return self.proc.read_data(7, int(address) << 9 | register) & 0xFF

    @asyncio.coroutine
    def i2c_read_block(self, address, register, count):
        """Read block via I2C."""
        result = []
        position = 0
        while position < count:
            if count - position == 1:
                data = yield from self.i2c_read8(int(address), register + position)
                result.append(data)
                position += 1
            else:
                data = yield from self.i2c_read16(int(address), register)
                result.append((data >> 8) & 0xFF)
                result.append(data & 0xFF)
                position += 2
        return result

    @asyncio.coroutine
    def i2c_read16(self, address, register):
        """Read an 16-bit value from the I2C bus of the P3-Roc."""
        return self.proc.read_data(7, int(address) << 9 | 1 << 8 | register)

    @classmethod
    def scale_accelerometer_to_g(cls, raw_value):
        """Convert internal representation to g."""
        # raw value is 0 to 16384 -> 14 bit
        # scale is -2g to 2g (2 complement)
        if raw_value & (1 << 13):
            raw_value -= 1 << 14

        g_value = float(raw_value) / (1 << 12)

        return g_value

    def configure_accelerometer(self, config, callback):
        """Configure the accelerometer on the P3-ROC."""
        config = self.machine.config_validator.validate_config("p3_roc_accelerometer", config)
        if config['number'] != 1:
            raise AssertionError("P3-ROC only has one accelerometer. Use number 1. Found: {}".format(config))

        self.accelerometer_device = PROCAccelerometer(callback)
        self._configure_accelerometer()

        return self.accelerometer_device

    def _configure_accelerometer(self):

        # enable polling every 128ms
        enable = 0x0F

        # configure some P3-Roc registers
        self.proc.write_data(6, 0x000, enable)

        # CTRL_REG1 - set to standby
        self.proc.write_data(6, 0x12A, 0)

        # XYZ_DATA_CFG - disable high pass filter, scale 0 to 2g
        self.proc.write_data(6, 0x10E, 0x00)

        # CTRL_REG1 - set device to active and in low noise mode
        # 800HZ output data rate
        self.proc.write_data(6, 0x12A, 0x05)

        # CTRL_REG2 - set no sleep, high resolution mode
        self.proc.write_data(6, 0x12B, 0x02)

        # for auto-polling of accelerometer every 128 ms (8 times a sec). set 0x0F
        # disable polling + IRQ status addr FF_MT_SRC
        self.proc.write_data(6, 0x000, 0x1E0F)
        # flush data to proc
        self.proc.flush()

    def get_info_string(self):
        """Dump infos about boards."""
        infos = "Firmware Version: {} Firmware Revision: {} Hardware Board ID: {}\n".format(
            self.version, self.revision, self.hardware_version)

        infos += "SW-16 boards found:\n"

        for board in range(0, 32):
            device_type = self.proc.read_data(2, (1 << 12) + (board << 6))
            board_id = self.proc.read_data(2, (1 << 12) + (board << 6) + 1)
            if device_type != 0:
                infos += " - Board: {} Switches: 16 Device Type: {:X} Board ID: {:X}\n".format(
                    board, device_type, board_id)

        return infos

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Create a P3-ROC driver.

        Typically drivers are coils or flashers, but for the P3-ROC this is
        also used for matrix-based lights.

        Args:
            config: Dictionary of settings for the driver.

        Returns:
            A reference to the PROCDriver object which is the actual object you
            can use to pulse(), patter(), enable(), etc.
        """
        # todo need to add virtual driver support for driver counts > 256

        # Find the P3-ROC number for each driver. For P3-ROC driver boards, the
        # P3-ROC number is specified via the Ax-By-C format.

        proc_num = self.pdbconfig.get_proc_coil_number(str(number))
        if proc_num == -1:
            raise AssertionError("Driver {} cannot be controlled by the P3-ROC. ".format(str(number)))

        proc_driver_object = PROCDriver(proc_num, config, self, number)

        return proc_driver_object

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict):
        """Configure a P3-ROC switch.

        Args:
            config: Dictionary of settings for the switch. In the case
                of the P3-ROC, it uses the following:

        Returns: A configured switch object.
        """
        del platform_config
        proc_num = self.pdbconfig.get_proc_switch_number(str(number))
        return self._configure_switch(config, proc_num)

    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Read in and set the initial switch state.

        The P-ROC uses the following values for hw switch states:
        1 - closed (debounced)
        2 - open (debounced)
        3 - closed (not debounced)
        4 - open (not debounced)
        """
        states = self.proc.switch_get_states()

        for switch, state in enumerate(states):
            # Note: The P3-ROC will return a state of "3" for switches from non-
            # connected SW-16 boards, so that's why we only check for "1" below
            if state == 1:
                states[switch] = 1
            else:
                states[switch] = 0

        return states

    def tick(self):
        """Check the P3-ROC for any events (switch state changes).

        Also tickles the watchdog and flushes any queued commands to the P3-ROC.
        """
        # Get P3-ROC events
        for event in self.proc.get_events():
            event_type = event['type']
            event_value = event['value']
            if event_type == self.pinproc.EventTypeSwitchClosedDebounced:
                self.machine.switch_controller.process_switch_by_num(state=1,
                                                                     num=event_value,
                                                                     platform=self)
            elif event_type == self.pinproc.EventTypeSwitchOpenDebounced:
                self.machine.switch_controller.process_switch_by_num(state=0,
                                                                     num=event_value,
                                                                     platform=self)
            elif event_type == self.pinproc.EventTypeSwitchClosedNondebounced:
                self.machine.switch_controller.process_switch_by_num(state=1,
                                                                     num=event_value,
                                                                     platform=self)
            elif event_type == self.pinproc.EventTypeSwitchOpenNondebounced:
                self.machine.switch_controller.process_switch_by_num(state=0,
                                                                     num=event_value,
                                                                     platform=self)

            # The P3-ROC will always send all three values sequentially.
            # Therefore, we will trigger after the Z value
            elif event_type == self.pinproc.EventTypeAccelerometerX:
                self.acceleration[0] = event_value
                self.debug_log("Got Accelerometer value X. Value: %s", event_value)
            elif event_type == self.pinproc.EventTypeAccelerometerY:
                self.acceleration[1] = event_value
                self.debug_log("Got Accelerometer value Y. Value: %s", event_value)
            elif event_type == self.pinproc.EventTypeAccelerometerZ:
                self.acceleration[2] = event_value

                # trigger here
                if self.accelerometer_device:
                    self.accelerometer_device.update_acceleration(
                        self.scale_accelerometer_to_g(self.acceleration[0]),
                        self.scale_accelerometer_to_g(self.acceleration[1]),
                        self.scale_accelerometer_to_g(self.acceleration[2]))
                    self.debug_log("Got Accelerometer value Z. Value: %s", event_value)

            else:   # pragma: no cover
                self.log.warning("Received unrecognized event from the P3-ROC. "
                                 "Type: %s, Value: %s", event_type, event_value)

        self.proc.watchdog_tickle()
        self.proc.flush()


class PROCAccelerometer(AccelerometerPlatformInterface):

    """The accelerometer on the P3-Roc."""

    def __init__(self, callback: "Accelerometer") -> None:
        """Remember the callback."""
        self.callback = callback    # type: Accelerometer

    def update_acceleration(self, x: float, y: float, z: float) -> None:
        """Call the callback."""
        self.callback.update_acceleration(x, y, z)
