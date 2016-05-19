"""Contains code for a virtual hardware platform."""

import logging
import random

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.core.platform import ServoPlatform, MatrixLightsPlatform, GiPlatform, LedPlatform, \
    SwitchPlatform, DriverPlatform, AccelerometerPlatform, I2cPlatform
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.core.rgb_color import RGBColor


class HardwarePlatform(AccelerometerPlatform, I2cPlatform, ServoPlatform, MatrixLightsPlatform, GiPlatform,
                       LedPlatform, SwitchPlatform, DriverPlatform):
    """Base class for the virtual hardware platform."""

    def __init__(self, machine):
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger("Virtual Platform")
        self.log.debug("Configuring virtual hardware interface.")

        # Since the virtual platform doesn't have real hardware, we need to
        # maintain an internal list of switches that were confirmed so we have
        # something to send when MPF needs to know the hardware states of
        # switches
        self.hw_switches = dict()
        self.initial_states_sent = False

    def __repr__(self):
        return '<Platform.Virtual>'

    def initialize(self):
        pass

    def stop(self):
        pass

    def configure_driver(self, config):
        # generate random number if None
        if config['number'] is None:
            config['number'] = random.randint(100, 10000)

        driver = VirtualDriver(config)

        return driver

    def configure_switch(self, config):
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
        sections = []
        for platform in self._get_platforms():
            if hasattr(platform, "get_switch_config_section") and platform.get_switch_config_section():
                sections.append(platform.get_switch_config_section())
        self.machine.config_validator.validate_config(
            "switches", config, switch.name,
            base_spec=sections)
        return config

    def validate_switch_overwrite_section(self, switch, config_overwrite):
        sections = []
        for platform in self._get_platforms():
            if hasattr(platform, "get_switch_overwrite_section") and platform.get_switch_overwrite_section():
                sections.append(platform.get_switch_overwrite_section())
        self.machine.config_validator.validate_config(
            "switch_overwrites", config_overwrite, switch.name,
            base_spec=sections)
        return config_overwrite

    def validate_coil_overwrite_section(self, driver, config_overwrite):
        sections = []
        for platform in self._get_platforms():
            if hasattr(platform, "get_coil_overwrite_section") and platform.get_coil_overwrite_section():
                sections.append(platform.get_coil_overwrite_section())
        self.machine.config_validator.validate_config(
            "coil_overwrites", config_overwrite, driver.name,
            base_spec=sections)
        return config_overwrite

    def validate_coil_section(self, driver, config):
        sections = []
        for platform in self._get_platforms():
            if hasattr(platform, "get_coil_config_section") and platform.get_coil_config_section():
                sections.append(platform.get_coil_config_section())
        self.machine.config_validator.validate_config(
            "coils", config, driver.name,
            base_spec=sections)
        return config

    def configure_accelerometer(self, device, number, use_high_pass):
        pass

    def configure_matrixlight(self, config):
        return VirtualMatrixLight(config['number'])

    def configure_led(self, config, channels):
        return VirtualLED(config['number'])

    def configure_gi(self, config):
        return VirtualGI(config['number'])

    def clear_hw_rule(self, switch, coil):
        pass

    def i2c_write8(self, address, register, value):
        pass

    def i2c_read8(self, address, register):
        del address
        del register
        return None

    def i2c_read16(self, address, register):
        del address
        del register
        return None

    def servo_go_to_position(self, number, position):
        pass

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        pass

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        pass

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        pass

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        pass


class VirtualSwitch(SwitchPlatformInterface):
    """Represents a switch in a pinball machine used with virtual hardware."""
    def __init__(self, config):
        super().__init__(config, config['number'])
        self.log = logging.getLogger('VirtualSwitch')


class VirtualMatrixLight(MatrixLightPlatformInterface):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualMatrixLight')
        self.number = number
        self.current_brightness = 0

    def on(self, brightness=255):
        self.current_brightness = brightness

    def off(self):
        self.current_brightness = 0


class VirtualLED(RGBLEDPlatformInterface):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualLED')
        self.number = number
        self.current_color = RGBColor()

    def color(self, color):
        self.current_color = color


class VirtualGI(GIPlatformInterface):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualGI')
        self.number = number
        self.current_brightness = 0

    def on(self, brightness=255):
        self.current_brightness = brightness

    def off(self):
        self.current_brightness = 0


class VirtualDriver(DriverPlatformInterface):
    def __init__(self, config):
        self.log = logging.getLogger('VirtualDriver')
        self.number = config['number']
        self.config = config

    def __repr__(self):
        return "VirtualDriver.{}".format(self.number)

    def disable(self, coil):
        pass

    def enable(self, coil):
        pass

    def pulse(self, coil, milliseconds):
        del coil
        return milliseconds

    def state(self):
        pass

    def tick(self):
        pass

    def reconfigure(self, polarity):
        pass
