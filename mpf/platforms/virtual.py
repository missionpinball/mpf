"""Contains code for a virtual hardware platform."""

import logging
import random

from mpf.platforms.interfaces.dmd_platform import DmdPlatformInterface
from mpf.platforms.interfaces.servo_platform_interface import ServoPlatformInterface
from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.core.platform import ServoPlatform, MatrixLightsPlatform, GiPlatform, LedPlatform, \
    SwitchPlatform, DriverPlatform, AccelerometerPlatform, I2cPlatform, DmdPlatform, RgbDmdPlatform
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.core.rgb_color import RGBColor


class HardwarePlatform(AccelerometerPlatform, I2cPlatform, ServoPlatform, MatrixLightsPlatform, GiPlatform,
                       LedPlatform, SwitchPlatform, DriverPlatform, DmdPlatform, RgbDmdPlatform):

    """Base class for the virtual hardware platform."""

    def __init__(self, machine):
        """Initialise virtual platform."""
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger("Virtual Platform")
        self.log.debug("Configuring virtual hardware interface.")

        # Since the virtual platform doesn't have real hardware, we need to
        # maintain an internal list of switches that were confirmed so we have
        # something to send when MPF needs to know the hardware states of
        # switches
        self.hw_switches = dict()
        self.initial_states_sent = False
        self.features['tickless'] = True

    def __repr__(self):
        """Return string representation."""
        return '<Platform.Virtual>'

    def initialize(self):
        """Initialise platform."""
        pass

    def stop(self):
        """Stop platform."""
        pass

    def configure_servo(self, config):
        """Configure a servo device in paltform."""
        return VirtualServo(config['number'])

    def configure_driver(self, config):
        """Configure driver."""
        # generate random number if None
        if config['number'] is None:
            config['number'] = random.randint(100, 10000)

        driver = VirtualDriver(config)

        return driver

    def configure_switch(self, config):
        """Configure switch."""
        # We want to have the virtual platform set all the initial switch states
        # to inactive, so we have to check the config.

        state = 0

        if config['type'].upper() == 'NC':
            state = 1

        # switch needs a number to be distingishable from other switches
        if config['number'] is None:
            config['number'] = random.randint(100, 10000)

        self.hw_switches[config['number']] = state

        return VirtualSwitch(config)

    def get_hw_switch_states(self):
        """Return hw switch states."""
        if not self.initial_states_sent:

            if 'virtual_platform_start_active_switches' in self.machine.config:

                initial_active_switches = [self.machine.switches[x].hw_switch.number for x in
                                           Util.string_to_list(
                                               self.machine.config['virtual_platform_start_active_switches'])]

                for k in self.hw_switches:
                    if k in initial_active_switches:
                        self.hw_switches[k] ^= 1

            self.initial_states_sent = True

        else:
            switches = [x for x in self.machine.switches if x.platform == self]

            for switch in switches:
                self.hw_switches[switch.hw_switch.number] = switch.state ^ switch.invert

        return self.hw_switches

    def _get_platforms(self):
        platforms = []
        for name, platform in self.machine.config['mpf']['platforms'].items():
            if name == "virtual" or name == "smart_virtual":
                continue
            platforms.append(Util.string_to_class(platform))
        return platforms

    def validate_switch_section(self, switch, config):
        """Validate switch sections."""
        sections = ["device"]
        for platform in self._get_platforms():
            if hasattr(platform, "get_switch_config_section") and platform.get_switch_config_section():
                sections.append(platform.get_switch_config_section())
        self.machine.config_validator.validate_config(
            "switches", config, switch.name,
            base_spec=sections)
        return config

    def validate_switch_overwrite_section(self, switch, config_overwrite):
        """Validate switch overwrite sections."""
        sections = []
        for platform in self._get_platforms():
            if hasattr(platform, "get_switch_overwrite_section") and platform.get_switch_overwrite_section():
                sections.append(platform.get_switch_overwrite_section())
        self.machine.config_validator.validate_config(
            "switch_overwrites", config_overwrite, switch.name,
            base_spec=sections)
        return config_overwrite

    def validate_coil_overwrite_section(self, driver, config_overwrite):
        """Validate coil overwrite sections."""
        sections = []
        for platform in self._get_platforms():
            if hasattr(platform, "get_coil_overwrite_section") and platform.get_coil_overwrite_section():
                sections.append(platform.get_coil_overwrite_section())
        self.machine.config_validator.validate_config(
            "coil_overwrites", config_overwrite, driver.name,
            base_spec=sections)
        return config_overwrite

    def validate_coil_section(self, driver, config):
        """Validate coil sections."""
        sections = ["device"]
        for platform in self._get_platforms():
            if hasattr(platform, "get_coil_config_section") and platform.get_coil_config_section():
                sections.append(platform.get_coil_config_section())
        self.machine.config_validator.validate_config(
            "coils", config, driver.name,
            base_spec=sections)
        return config

    def configure_accelerometer(self, config, callback):
        """Configure accelerometer."""
        pass

    def configure_matrixlight(self, config):
        """Configure matrix light."""
        return VirtualMatrixLight(config['number'])

    def configure_led(self, config, channels):
        """Configure led."""
        return VirtualLED(config['number'])

    def configure_gi(self, config):
        """Configure GI."""
        return VirtualGI(config['number'])

    def clear_hw_rule(self, switch, coil):
        """Clear hw rule."""
        pass

    def i2c_write8(self, address, register, value):
        """Write to I2C."""
        pass

    def i2c_read8(self, address, register):
        """Read I2C."""
        del address
        del register
        return None

    def i2c_read16(self, address, register):
        """Read I2C."""
        del address
        del register
        return None

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set rule."""
        pass

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set rule."""
        pass

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set rule."""
        pass

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set rule."""
        pass

    def configure_dmd(self):
        """Configure DMD."""
        return VirtualDmd()

    def configure_rgb_dmd(self):
        """Configure DMD."""
        return VirtualDmd()


class VirtualDmd(DmdPlatformInterface):

    """Virtual DMD."""

    def __init__(self):
        """Initialise virtual DMD."""
        self.data = None

    def update(self, data: bytes):
        """Update data on the DMD.

        Args:
            data: bytes to send to DMD
        """
        self.data = data


class VirtualSwitch(SwitchPlatformInterface):

    """Represents a switch in a pinball machine used with virtual hardware."""

    def __init__(self, config):
        """Initialise switch."""
        super().__init__(config, config['number'])
        self.log = logging.getLogger('VirtualSwitch')


class VirtualMatrixLight(MatrixLightPlatformInterface):

    """Virtual matrix light."""

    def __init__(self, number):
        """Initialise matrix light."""
        self.log = logging.getLogger('VirtualMatrixLight')
        self.number = number
        self.current_brightness = 0

    def on(self, brightness=255):
        """Turn on matrix light."""
        self.current_brightness = brightness

    def off(self):
        """Turn off matrix light."""
        self.current_brightness = 0


class VirtualLED(RGBLEDPlatformInterface):

    """Virtual LED."""

    def __init__(self, number):
        """Initialise LED."""
        self.log = logging.getLogger('VirtualLED')
        self.number = number
        self.current_color = list(RGBColor().rgb)

    def color(self, color):
        """Set color."""
        self.current_color = color


class VirtualGI(GIPlatformInterface):

    """Virtual GI."""

    def __init__(self, number):
        """Initialise GI."""
        self.log = logging.getLogger('VirtualGI')
        self.number = number
        self.current_brightness = 0

    def on(self, brightness=255):
        """Turn GI on."""
        self.current_brightness = brightness

    def off(self):
        """Turn GI off."""
        self.current_brightness = 0


class VirtualServo(ServoPlatformInterface):

    """Virtual servo."""

    def __init__(self, number):
        """Initialise servo."""
        self.log = logging.getLogger('VirtualServo')
        self.number = number
        self.current_position = None

    def go_to_position(self, position):
        """Go to position."""
        self.current_position = position


class VirtualDriver(DriverPlatformInterface):

    """A virtual driver object."""

    def __init__(self, config):
        """Initialise virtual driver to disabled."""
        self.log = logging.getLogger('VirtualDriver')
        super().__init__(config, config['number'])
        self.state = "disabled"

    def get_board_name(self):
        """Return the name of the board of this driver."""
        return "Virtual"

    def __repr__(self):
        """Str representation."""
        return "VirtualDriver.{}".format(self.number)

    def disable(self, coil):
        """Disable virtual coil."""
        del coil
        self.state = "disabled"

    def enable(self, coil):
        """Enable virtual coil."""
        del coil
        # pylint: disable-msg=too-many-boolean-expressions
        if (not self.config.get("allow_enable", False) and not self.config.get("hold_power", 0) and     # defaults
                not self.config.get("pwm_on_ms", 0) and not self.config.get("pwm_off_ms", 0) and        # p-roc
                not self.config.get("hold_power32", 0) and not self.config.get("hold_pwm_mask", 0) and  # fast
                not self.config.get("hold_power16", 0)):                                                # opp
            raise AssertionError("Cannot enable coil {}. Please specify allow_enable or hold_power".format(self.number))

        self.state = "enabled"

    def pulse(self, coil, milliseconds):
        """Pulse virtual coil."""
        del coil
        self.state = "pulsed_" + str(milliseconds)
        return milliseconds
