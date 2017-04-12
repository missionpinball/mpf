"""Contains the parent class for all platforms."""
import abc
from collections import namedtuple

from typing import Optional

from mpf.devices.switch import Switch
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class BasePlatform(metaclass=abc.ABCMeta):

    """Base class for all hardware platforms in MPF."""

    def __init__(self, machine):
        """Create features and set default variables.

        Args:
            machine(mpf.core.machine.MachineController:
        """
        self.machine = machine
        self.features = {}
        self.log = None
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

    def debug_log(self, msg, *args, **kwargs):
        """Log when debug is set to True for platform."""
        if self.debug:
            self.log.debug(msg, *args, **kwargs)

    @abc.abstractmethod
    def initialize(self):
        """Initialise the platform.

        This is called after all platforms have been created and core modules have been loaded.
        """
        pass

    def tick(self):
        """Called once per machine loop.

        Subclass this method in a platform module to perform periodic updates
        to the platform hardware, e.g. reading switches, sending driver or
        light updates, etc.

        """
        pass

    @abc.abstractmethod
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


class RgbDmdPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for RGB DMDs in MPF."""

    def __init__(self, machine):
        """Add rgb dmd feature."""
        super().__init__(machine)
        self.features['has_rgb_dmd'] = True

    @abc.abstractmethod
    def configure_rgb_dmd(self):
        """Subclass this method in a platform module to configure the DMD.

        This method should return a reference to the DMD's platform interface
        method will will receive the frame data.

        """
        raise NotImplementedError


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
    def i2c_read8(self, address, register):
        """Read an 8-bit value from an address and register via I2C.

        Args:
            address (int): I2C Address
            register (int): Register
        """
        raise NotImplementedError

    @abc.abstractmethod
    def i2c_read16(self, address, register):
        """Read an 16-bit value from an address and register via I2C.

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
    def configure_servo(self, config):
        """Configure a servo device in paltform.

        Args:
            config (dict): Configuration of device
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
        """Called after channels of a light were updated.

        Can be used if multiple channels need to be flushed at once.
        """
        pass

    @abc.abstractmethod
    def configure_light(self, number, subtype, platform_settings) -> LightPlatformInterface:
        """Subclass this method in a platform module to configure a light.

        This method should return a reference to the light
        object which will be called to access the hardware.
        """
        raise NotImplementedError


class SwitchPlatform(BasePlatform, metaclass=abc.ABCMeta):

    """Baseclass for platforms with switches in MPF."""

    def __init__(self, machine):
        """Add switch feature."""
        super().__init__(machine)
        self.features['has_switches'] = True

    @abc.abstractmethod
    def configure_switch(self, config):
        """Subclass this method in a platform module to configure a switch.

        This method should return a reference to the switch's platform interface
        object which will be called to access the hardware.

        Args:
            config (dict): Config of switch.

        """
        raise NotImplementedError

    @classmethod
    def get_switch_config_section(cls) -> Optional[str]:
        """Return config section for additional switch config items."""
        return None

    def validate_switch_section(self, switch: Switch, config: dict) -> dict:
        """Validate a switch config for platform.

        Args:
            switch: Switch to validate.
            config: Config to validate.

        Returns: Validated config.
        """
        base_spec = ["device"]
        if self.get_switch_config_section():
            base_spec.append(self.get_switch_config_section())
        switch.machine.config_validator.validate_config(
            "switches", config, switch.name,
            base_spec=base_spec)
        return config

    @abc.abstractmethod
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
    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
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

    def validate_coil_section(self, driver, config):
        """Validate coil config for platform."""
        if self.__class__.get_coil_config_section():
            spec = self.__class__.get_coil_config_section()
            config = driver.machine.config_validator.validate_config(
                spec, config, driver.name)
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
