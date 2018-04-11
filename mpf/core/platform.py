"""Contains the parent class for all platforms."""
import abc
import asyncio
from collections import namedtuple

from typing import Optional

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.switch import Switch
    from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
    from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
    from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface
    from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface
    from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface
    from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface
    from logging import Logger
    from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface


class BasePlatform(metaclass=abc.ABCMeta):

    """Base class for all hardware platforms in MPF."""

    def __init__(self, machine):
        """Create features and set default variables.

        Args:
            machine(mpf.core.machine.MachineController:
        """
        self.machine = machine
        self.features = {}
        self.log = None         # type: Logger
        self.debug = False

        # Set default platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['has_dmd'] = False
        self.features['has_rgb_dmd'] = False
        self.features['has_accelerometers'] = False
        self.features['has_i2c'] = False
        self.features['has_servos'] = False
        self.features['has_lights'] = False
        self.features['has_switches'] = False
        self.features['has_drivers'] = False
        self.features['tickless'] = False
        self.features['segment_display'] = False
        self.features['hardware_sounds'] = False
        self.features['has_steppers'] = False

    # pylint: disable-msg=no-self-use
    def get_info_string(self) -> str:
        """Return information string about this platform."""
        return "Not implemented"

    # pylint: disable-msg=no-self-use
    def update_firmware(self) -> str:
        """Perform a firmware update."""
        pass

    def debug_log(self, msg, *args, **kwargs):
        """Log when debug is set to True for platform."""
        if self.debug:
            self.log.debug(msg, *args, **kwargs)

    @asyncio.coroutine
    def initialize(self):
        """Initialise the platform.

        This is called after all platforms have been created and core modules have been loaded.
        """
        pass

    @asyncio.coroutine
    def start(self):
        """Start receiving switch changes from this platform."""
        pass

    def tick(self):
        """Run task.

        Called periodically.

        Subclass this method in a platform module to perform periodic updates
        to the platform hardware, e.g. reading switches, sending driver or
        light updates, etc.

        """
        pass

    def stop(self):
        """Stop the platform.

        Subclass this method in the platform module if you need to perform
        any actions to gracefully stop the platform interface.

        This could do things like reseting it, stopping events, etc.

        This method will be called when MPF stops, including when an MPF thread
        crashes.

        """
        pass


class DmdPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for DMDs in MPF."""

    def __init__(self, machine):
        """Add dmd feature."""
        super().__init__(machine)
        self.features['has_dmd'] = True

    @abc.abstractmethod
    def configure_dmd(self):
        """Subclass this method in a platform module to configure the DMD.

        This method should return a reference to the DMD's platform interface
        method will will receive the frame data.

        """
        raise NotImplementedError


class HardwareSoundPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for hardware sounds in MPF."""

    def __init__(self, machine):
        """Add hardware sound feature."""
        super().__init__(machine)
        self.features['hardware_sounds'] = True

    @abc.abstractmethod
    def configure_hardware_sound_system(self) -> "HardwareSoundPlatformInterface":
        """Return a reference to the hardware sound interface."""
        raise NotImplementedError


class RgbDmdPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for RGB DMDs in MPF."""

    def __init__(self, machine):
        """Add rgb dmd feature."""
        super().__init__(machine)
        self.features['has_rgb_dmd'] = True

    @abc.abstractmethod
    def configure_rgb_dmd(self, name: str):
        """Subclass this method in a platform module to configure the DMD.

        This method should return a reference to the DMD's platform interface
        method will will receive the frame data.

        """
        raise NotImplementedError


class SegmentDisplayPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for 7-segment/6-digits display in MPF."""

    def __init__(self, machine):
        """Add segment display feature."""
        super().__init__(machine)
        self.features['segment_display'] = True

    @abc.abstractmethod
    def configure_segment_display(self, number: str) -> "SegmentDisplayPlatformInterface":
        """Subclass this method in a platform module to configure a segment display.

        This method should return a reference to the segment display platform interface
        method will will receive the text to show.
        """
        raise NotImplementedError


# pylint: disable-msg=abstract-method
class SegmentDisplaySoftwareFlashPlatform(SegmentDisplayPlatform, metaclass=abc.ABCMeta):

    """SegmentDisplayPlatform with software flash support."""

    def __init__(self, machine):
        """Initialise software flash support."""
        super().__init__(machine)
        self._displays = set()
        self._display_flash_task = None

    @asyncio.coroutine
    def initialize(self):
        """Start flash task."""
        yield from super().initialize()
        self._display_flash_task = self.machine.clock.loop.create_task(self._display_flash())
        self._display_flash_task.add_done_callback(self._display_flash_task_done)

    @asyncio.coroutine
    def _display_flash(self):
        wait_time = 1 / (self.config['display_flash_frequency'] * 2)
        while True:
            # set on
            yield from asyncio.sleep(wait_time, loop=self.machine.clock.loop)
            for display in self._displays:
                display.set_software_flash(True)
            # set off
            yield from asyncio.sleep(wait_time, loop=self.machine.clock.loop)
            for display in self._displays:
                display.set_software_flash(False)

    @staticmethod
    def _display_flash_task_done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def stop(self):
        """Cancel flash task."""
        super().stop()
        if self._display_flash_task:
            self._display_flash_task.cancel()

    def _handle_software_flash(self, display):
        """Register display for flash task."""
        self._displays.add(display)


class AccelerometerPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for Accelerometer platforms."""

    def __init__(self, machine):
        """Add accelerometer feature."""
        super().__init__(machine)
        self.features['has_accelerometers'] = True

    @abc.abstractmethod
    def configure_accelerometer(self, config, callback):
        """Configure accelerometer.

        Args:
            config (dict): Configuration of this accelerometer
            callback (mpf.devices.accelerometer.Accelerometer): Callback device to send data to
        """
        raise NotImplementedError


class I2cPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for I2C Platforms."""

    def __init__(self, machine):
        """Initialise I2C platform and set feature."""
        super().__init__(machine)
        self.features['has_i2c'] = True

    @abc.abstractmethod
    def i2c_write8(self, address, register, value):
        """Write an 8-bit value to a specific address and register via I2C.

        Args:
            address (int): I2C address
            register (int): Register
            value (int): Value to write
        """
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def i2c_read_block(self, address, register, count):
        """Read an len bytes from an address and register via I2C.

        Args:
            address (int): I2C Address
            register (int): Register
            count (int): Bytes to read
        """
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def i2c_read8(self, address, register):
        """Read an 8-bit value from an address and register via I2C.

        Args:
            address (int): I2C Address
            register (int): Register
        """
        raise NotImplementedError


class ServoPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for servo platforms in MPF."""

    def __init__(self, machine):
        """Add servo feature."""
        super().__init__(machine)
        self.features['has_servos'] = True

    @abc.abstractmethod
    def configure_servo(self, number: str) -> "ServoPlatformInterface":
        """Configure a servo device in paltform.

        Args:
            number: Number of the servo
        """
        raise NotImplementedError


class StepperPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for smart servo (axis) platforms in MPF."""

    def __init__(self, machine):
        """Add smart servo feature."""
        super().__init__(machine)
        self.features['has_steppers'] = True

    @abc.abstractmethod
    def configure_stepper(self, number: str, config: dict) -> "StepperPlatformInterface":
        """Configure a smart stepper (axis) device in paltform.

        Args:
            number: Number of the smart servo
        """
        raise NotImplementedError


class LightsPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for platforms with any kind of lights in MPF.

    This includes LEDs, GIs, Matrix Lights and any other lights.
    """

    def __init__(self, machine):
        """Add led feature."""
        super().__init__(machine)
        self.features['has_lights'] = True

    @abc.abstractmethod
    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light number to a list of channels."""
        raise NotImplementedError

    def light_sync(self):
        """Update lights synchonously.

        Called after channels of a light were updated. Can be used if multiple channels need to be flushed at once.
        """
        pass

    @abc.abstractmethod
    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> "LightPlatformInterface":
        """Subclass this method in a platform module to configure a light.

        This method should return a reference to the light
        object which will be called to access the hardware.
        """
        raise NotImplementedError


SwitchConfig = namedtuple("SwitchConfig", ["invert", "debounce"])


class SwitchPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for platforms with switches in MPF."""

    def __init__(self, machine):
        """Add switch feature."""
        super().__init__(machine)
        self.features['has_switches'] = True

    @abc.abstractmethod
    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Subclass this method in a platform module to configure a switch.

        This method should return a reference to the switch's platform interface
        object which will be called to access the hardware.

        Args:
            config : Config of switch.

        """
        raise NotImplementedError

    @classmethod
    def get_switch_config_section(cls) -> Optional[str]:
        """Return config section for additional switch config items."""
        return None

    def validate_switch_section(self, switch: "Switch", config: dict) -> dict:
        """Validate a switch config for platform.

        Args:
            switch: Switch to validate.
            config: Config to validate.

        Returns: Validated config.
        """
        if self.get_switch_config_section():
            spec = self.get_switch_config_section()
            config = switch.machine.config_validator.validate_config(spec, config, switch.name)
        elif config:
            raise AssertionError("No platform_config supported but not empty {} for switch {}".
                                 format(config, switch.name))

        return config

    @abc.abstractmethod
    @asyncio.coroutine
    def get_hw_switch_states(self):
        """Get all hardware switch states.

        Subclass this method in a platform module to return the hardware
        states of all the switches on that platform.
        of a switch.

        This method should return a dict with the switch numbers as keys and the
        hardware state of the switches as values. (0 = inactive, 1 = active)
        This method should not compensate for NO or NC status, rather, it
        should return the raw hardware states of the switches.

        """
        raise NotImplementedError


SwitchSettings = namedtuple("SwitchSettings", ["hw_switch", "invert", "debounce"])
DriverSettings = namedtuple("DriverSettings", ["hw_driver", "pulse_settings", "hold_settings", "recycle"])
DriverConfig = namedtuple("DriverConfig", ["default_pulse_ms", "default_pulse_power", "default_hold_power",
                                           "default_recycle", "max_pulse_ms", "max_pulse_power", "max_hold_power"])


class DriverPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for platforms with drivers."""

    def __init__(self, machine):
        """Add driver feature and default max_pulse length."""
        super().__init__(machine)

        # Set default platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['has_drivers'] = True
        self.features['max_pulse'] = 255

    @abc.abstractmethod
    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict) -> "DriverPlatformInterface":
        """Subclass this method in a platform module to configure a driver.

        This method should return a reference to the driver's platform interface
        object which will be called to access the hardware.

        """
        raise NotImplementedError

    @abc.abstractmethod
    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Subclass this method in a platform module to clear a hardware switch rule for this switch.

        Clearing a hardware rule means actions on this switch will no longer
        affect coils.

        Another way to think of this is that it 'disables' a hardware rule.
        This is what you'd use to disable flippers and autofire_coils during
        tilt, game over, etc.

        """
        raise NotImplementedError

    @classmethod
    def get_coil_config_section(cls) -> Optional[str]:
        """Return addition config section for coils."""
        return None

    def validate_coil_section(self, driver, config) -> dict:
        """Validate coil config for platform."""
        if self.get_coil_config_section():
            spec = self.get_coil_config_section()
            config = driver.machine.config_validator.validate_config(spec, config, driver.name)
        elif config:
            raise AssertionError("No platform_config supported but not empty {} for driver {}".
                                 format(config, driver.name))

        return config

    @abc.abstractmethod
    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse is canceled. Typically used on
        the main coil for dual coil flippers without eos switch.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and relase rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. Typically used for single coil flippers.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. When the second disable_switch is hit the pulse is canceled
        and the driver gets disabled. Typically used on the main coil for dual coil flippers with eos switch.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse continues. Typically used for
        autofire coils such as pop bumpers.
        """
        raise NotImplementedError
