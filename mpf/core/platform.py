"""Contains the parent class for all platforms."""
import abc
import asyncio
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum

from typing import Optional, Dict, List, Any

from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.switch import Switch   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.stepper import Stepper     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.servo import Servo     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface  # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface  # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface    # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface    # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface     # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface   # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.stepper_platform_interface import StepperPlatformInterface    # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.accelerometer_platform_interface import AccelerometerPlatformInterface    # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.i2c_platform_interface import I2cPlatformInterface    # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface  # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import; # noqa


class BasePlatform(LogMixin, metaclass=abc.ABCMeta):

    """Base class for all hardware platforms in MPF."""

    __slots__ = ["machine", "features", "debug"]

    def __init__(self, machine):
        """Create features and set default variables.

        Args:
        ----
            machine(mpf.core.machine.MachineController): The machine.
        """
        self.machine = machine  # type: MachineController
        self.features = {}
        super().__init__()
        self.debug = False

        # Set default platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['has_dmds'] = False
        self.features['has_rgb_dmds'] = False
        self.features['has_accelerometers'] = False
        self.features['has_i2c'] = False
        self.features['has_servos'] = False
        self.features['has_lights'] = False
        self.features['has_switches'] = False
        self.features['has_drivers'] = False
        self.features['tickless'] = False
        self.features['has_segment_displays'] = False
        self.features['has_hardware_sound_systems'] = True
        self.features['has_steppers'] = False
        self.features['allow_empty_numbers'] = False
        self.features['hardware_eos_repulse'] = False

    def assert_has_feature(self, feature_name):
        """Assert that this platform has a certain feature or raise an exception otherwise."""
        if not self.features.get("has_{}".format(feature_name), False):
            self.raise_config_error("Platform {} does not support to configure {feature_name}. "
                                    "Please make sure the platform "
                                    "you configured for {feature_name} actually supports that type "
                                    "of devices.".format(self.__class__, feature_name=feature_name), 99)

    def _configure_device_logging_and_debug(self, logger_name, config, url_base=None):
        """Configure logging for platform."""
        if config['debug']:
            self.debug = True
            config['console_log'] = 'full'
            config['file_log'] = 'full'

        self.configure_logging(logger_name,
                               config['console_log'],
                               config['file_log'],
                               url_base=url_base)

    @classmethod
    def get_config_spec(cls):
        """Return config spec for this platform."""
        return False

    # pylint: disable-msg=no-self-use
    def get_info_string(self) -> str:
        """Return information string about this platform."""
        return "Not implemented"

    # pylint: disable-msg=no-self-use
    def update_firmware(self) -> str:
        """Perform a firmware update."""

    async def initialize(self):
        """initialize the platform.

        This is called after all platforms have been created and core modules have been loaded.
        """

    async def start(self):
        """Start receiving switch changes from this platform."""

    def tick(self):
        """Run task.

        Called periodically.

        Subclass this method in a platform module to perform periodic updates
        to the platform hardware, e.g. reading switches, sending driver or
        light updates, etc.

        """

    def stop(self):
        """Stop the platform.

        Subclass this method in the platform module if you need to perform
        any actions to gracefully stop the platform interface.

        This could do things like reseting it, stopping events, etc.

        This method will be called when MPF stops, including when an MPF thread
        crashes.

        """


class DmdPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for DMDs in MPF."""

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add dmd feature."""
        super().__init__(machine)
        self.features['has_dmds'] = True

    @abc.abstractmethod
    def configure_dmd(self) -> "DmdPlatformInterface":
        """Subclass this method in a platform module to configure the DMD.

        This method should return a reference to the DMD's platform interface
        method will will receive the frame data.

        """
        raise NotImplementedError


class HardwareSoundPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for hardware sounds in MPF."""

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add hardware sound feature."""
        super().__init__(machine)
        self.features['has_hardware_sound_systems'] = True

    @abc.abstractmethod
    def configure_hardware_sound_system(self, platform_settings: dict) -> "HardwareSoundPlatformInterface":
        """Return a reference to the hardware sound interface."""
        raise NotImplementedError


class RgbDmdPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for RGB DMDs in MPF."""

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add rgb dmd feature."""
        super().__init__(machine)
        self.features['has_rgb_dmds'] = True

    @abc.abstractmethod
    def configure_rgb_dmd(self, name: str) -> "DmdPlatformInterface":
        """Subclass this method in a platform module to configure the DMD.

        This method should return a reference to the DMD's platform interface
        method will will receive the frame data.

        """
        raise NotImplementedError


class SegmentDisplayPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for 7-segment/6-digits display in MPF."""

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add segment display feature."""
        super().__init__(machine)
        self.features['has_segment_displays'] = True

    @classmethod
    def get_segment_display_config_section(cls) -> Optional[str]:
        """Return addition config section for segment displays."""
        return None

    def validate_segment_display_section(self, segment_display, config) -> dict:
        """Validate segment display config for platform."""
        if self.get_segment_display_config_section():
            spec = self.get_segment_display_config_section()   # pylint: disable-msg=assignment-from-none
            config = segment_display.machine.config_validator.validate_config(spec, config, segment_display.name)
        elif config:
            raise AssertionError("No platform_config supported but not empty {} for segment display {}".
                                 format(config, segment_display.name))

        return config

    @abc.abstractmethod
    async def configure_segment_display(self, number: str, display_size: int,
                                        platform_settings) -> "SegmentDisplayPlatformInterface":
        """Subclass this method in a platform module to configure a segment display.

        This method should return a reference to the segment display platform interface
        method will will receive the text to show.
        """
        raise NotImplementedError


# pylint: disable-msg=abstract-method
class SegmentDisplaySoftwareFlashPlatform(SegmentDisplayPlatform, metaclass=abc.ABCMeta):

    """SegmentDisplayPlatform with software flash support."""

    def __init__(self, machine):
        """initialize software flash support."""
        super().__init__(machine)
        self._displays = set()
        self._display_flash_task = None

    async def initialize(self):
        """Start flash task."""
        await super().initialize()
        self._display_flash_task = asyncio.create_task(self._display_flash())
        self._display_flash_task.add_done_callback(Util.raise_exceptions)

    async def _display_flash(self):
        wait_time_on = self.config['display_flash_duty'] / self.config['display_flash_frequency']
        wait_time_off = (1 - self.config['display_flash_duty']) / self.config['display_flash_frequency']
        while True:
            # set on
            await asyncio.sleep(wait_time_on)
            for display in self._displays:
                display.set_software_flash(True)
            # set off
            await asyncio.sleep(wait_time_off)
            for display in self._displays:
                display.set_software_flash(False)

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

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add accelerometer feature."""
        super().__init__(machine)
        self.features['has_accelerometers'] = True

    @abc.abstractmethod
    def configure_accelerometer(self, number: str, config: dict, callback) -> "AccelerometerPlatformInterface":
        """Configure accelerometer.

        Args:
        ----
            number: Number of this accelerometer
            config (dict): Configuration of this accelerometer
            callback (mpf.devices.accelerometer.Accelerometer): Callback device to send data to
        """
        raise NotImplementedError


class I2cPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for I2C Platforms."""

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """initialize I2C platform and set feature."""
        super().__init__(machine)
        self.features['has_i2c'] = True

    async def configure_i2c(self, number: str) -> "I2cPlatformInterface":
        """Configure i2c device."""
        raise NotImplementedError


class ServoPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for servo platforms in MPF."""

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add servo feature."""
        super().__init__(machine)
        self.features['has_servos'] = True

    @abc.abstractmethod
    async def configure_servo(self, number: str, config: dict, platform_config: dict) -> "ServoPlatformInterface":
        """Configure a servo device in platform.

        Args:
        ----
            number: Number of the servo
            config: The config section for this servo
            platform_config: Platform specific settings.
        """
        raise NotImplementedError

    @classmethod
    def get_servo_config_section(cls) -> Optional[str]:
        """Return config section for additional servo config items."""
        return None

    def validate_servo_section(self, servo: "Servo", config: dict) -> dict:
        """Validate a servo config for platform.

        Args:
        ----
            servo: Servo to validate.
            config: Config to validate.

        Returns: Validated config.
        """
        if self.get_servo_config_section():
            spec = self.get_servo_config_section()     # pylint: disable-msg=assignment-from-none
            config = servo.machine.config_validator.validate_config(spec, config, servo.name)
        elif config:
            raise AssertionError("No platform_config supported but not empty {} for servo {}".
                                 format(config, servo.name))

        return config


class StepperPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for smart servo (axis) platforms in MPF."""

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add smart servo feature."""
        super().__init__(machine)
        self.features['has_steppers'] = True

    @classmethod
    def get_stepper_config_section(cls) -> Optional[str]:
        """Return config section for additional stepper config items."""
        return None

    def validate_stepper_section(self, stepper: "Stepper", config: dict) -> dict:
        """Validate a stepper config for platform.

        Args:
        ----
            stepper: Stepper to validate.
            config: Config to validate.

        Returns: Validated config.
        """
        if self.get_stepper_config_section():
            spec = self.get_stepper_config_section()    # pylint: disable-msg=assignment-from-none
            config = stepper.machine.config_validator.validate_config(spec, config, stepper.name)
        elif config:
            raise AssertionError("No platform_config supported but not empty {} for stepper {}".
                                 format(config, stepper.name))

        return config

    @abc.abstractmethod
    async def configure_stepper(self, number: str, config: dict) -> "StepperPlatformInterface":
        """Configure a smart stepper (axis) device in platform.

        Args:
        ----
            number: Number of the smart servo
            config: Config for this stepper.
        """
        raise NotImplementedError


class LightConfigColors(Enum):

    """Light color for LightConfig."""

    RED = 1
    GREEN = 2
    BLUE = 3
    WHITE = 4
    NONE = 5


LightConfig = namedtuple("LightConfig", ["name", "color"])


class LightsPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for platforms with any kind of lights in MPF.

    This includes LEDs, GIs, Matrix Lights and any other lights.
    """

    __slots__ = []  # type: List[str]

    def __init__(self, machine):
        """Add led feature."""
        super().__init__(machine)
        self.features['has_lights'] = True

    @abc.abstractmethod
    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light number to a list of channels."""
        raise NotImplementedError

    def light_sync(self):
        """Update lights synchronously.

        Called after channels of a light were updated. Can be used if multiple channels need to be flushed at once.
        """

    @abc.abstractmethod
    def configure_light(self, number: str, subtype: str, config: LightConfig,
                        platform_settings: dict) -> "LightPlatformInterface":
        """Subclass this method in a platform module to configure a light.

        This method should return a reference to the light
        object which will be called to access the hardware.
        """
        raise NotImplementedError


SwitchConfig = namedtuple("SwitchConfig", ["name", "invert", "debounce"])


class SwitchPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for platforms with switches in MPF."""

    __slots__ = []  # type: List[str]

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
        ----
            number: Switch number.
            config : Config of switch.
            platform_config: Platform specific settings.

        """
        raise NotImplementedError

    @classmethod
    def get_switch_config_section(cls) -> Optional[str]:
        """Return config section for additional switch config items."""
        return None

    def validate_switch_section(self, switch: "Switch", config: dict) -> dict:
        """Validate a switch config for platform.

        Args:
        ----
            switch: Switch to validate.
            config: Config to validate.

        Returns: Validated config.
        """
        if self.get_switch_config_section():
            spec = self.get_switch_config_section()     # pylint: disable-msg=assignment-from-none
            config = switch.machine.config_validator.validate_config(spec, config, switch.name)
        elif config:
            raise AssertionError("No platform_config supported but not empty {} for switch {}".
                                 format(config, switch.name))

        return config

    @abc.abstractmethod
    async def get_hw_switch_states(self) -> Dict[str, bool]:
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


@dataclass
class SwitchSettings:
    hw_switch: Any
    invert: Any
    debounce: Any

@dataclass
class DriverSettings:
    hw_driver: Any
    pulse_settings: Any
    hold_settings: Any
    recycle: Any

@dataclass
class DriverConfig:
    name: str
    default_pulse_ms: int
    default_pulse_power: float
    default_hold_power: float
    default_timed_enable_ms: int
    default_recycle: bool
    max_pulse_ms: int
    max_pulse_power: float
    max_hold_power: float

@dataclass
class RepulseSettings:
    enable_repulse: bool
    debounce_ms: int



class DriverPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for platforms with drivers."""

    __slots__ = []  # type: List[str]

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
            spec = self.get_coil_config_section()   # pylint: disable-msg=assignment-from-none
            config = driver.machine.config_validator.validate_config(spec, config, driver.name)
        elif config:
            raise AssertionError("No platform_config supported but not empty {} for driver {}".
                                 format(config, driver.name))

        return config

    @abc.abstractmethod
    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse continues. Typically used for
        autofire coils such as pop bumpers.
        """
        raise NotImplementedError

    # pylint: disable-msg=no-self-use
    def set_delayed_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings, delay_ms: int):
        """Set pulse on hit and release rule to driver.

        When a switch is hit and a certain delay passed it pulses a driver.
        When the switch is released the pulse continues.
        Typically used for kickbacks.
        """
        del enable_switch
        del coil
        del delay_ms
        raise AssertionError("This platform does not support delayed pulse hardware rules.")

    @abc.abstractmethod
    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse is canceled. Typically used on
        the main coil for dual coil flippers without eos switch.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. Typically used for single coil flippers.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_pulse_on_hit_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                      eos_switch: SwitchSettings, coil: DriverSettings,
                                                      repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. When the switch is released
        the pulse is canceled and the driver gets disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes disabled. Typically used on the main coil for dual-wound coil flippers with eos switch.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 eos_switch: SwitchSettings, coil: DriverSettings,
                                                                 repulse_settings: Optional[RepulseSettings]):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver becomes disabled. When the eos_switch is hit the pulse is canceled
        and the driver becomes enabled (likely with PWM).
        Typically used on the coil for single-wound coil flippers with eos switch.
        """
        raise NotImplementedError
