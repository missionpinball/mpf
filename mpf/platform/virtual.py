"""Contains code for a virtual hardware platform."""

import logging
from mpf.system.platform import Platform
from mpf.system.utility_functions import Util
from mpf.platform.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platform.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platform.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platform.interfaces.driver_platform_interface import DriverPlatformInterface
from mpf.system.rgb_color import RGBColor


class HardwarePlatform(Platform):
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

        # ----------------------------------------------------------------------
        # Platform-specific hardware features. WARNING: Do not edit these. They
        # are based on what the virtual hardware can and cannot do.
        self.features['max_pulse'] = 255
        self.features['hw_timer'] = False
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False
        self.features['variable_debounce_time'] = False

        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features
        # ----------------------------------------------------------------------

    def __repr__(self):
        return '<Platform.Virtual>'

    def configure_driver(self, config, device_type='coil'):
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?

        driver = VirtualDriver(config['number'])

        driver.driver_settings = config
        driver.driver_settings['pulse_ms'] = 30

        return driver, config['number']

    def configure_switch(self, config):
        # We want to have the virtual platform set all the initial switch states
        # to inactive, so we have to check the config.

        state = 0

        if config['type'].upper() == 'NC':
            state = 1

        self.hw_switches[config['number']] = state

        switch = VirtualSwitch(config['number'])

        switch.driver_settings = config

        return switch, config['number']

    def get_hw_switch_states(self):

        if not self.initial_states_sent:

            if 'virtual_platform_start_active_switches' in self.machine.config:

                initial_active_switches = [self.machine.switches[x].number for x in
                    Util.string_to_list(
                        self.machine.config['virtual_platform_start_active_switches'])]

                for k, v in self.hw_switches.items():
                    if k in initial_active_switches:
                        self.hw_switches[k] ^= 1

            self.initial_states_sent = True

        else:
            switches = [x for x in self.machine.switches if x.platform == self]

            for switch in switches:
                self.hw_switches[switch.number] = switch.state ^ switch.invert

        return self.hw_switches

    def configure_accelerometer(self, device, number, useHighPass):
        pass

    def configure_matrixlight(self, config):
        return VirtualMatrixLight(config['number']), config['number']

    def configure_led(self, config):
        return VirtualLED(config['number'])

    def configure_gi(self, config):
        return VirtualGI(config['number']), config['number']

    def configure_dmd(self):
        return VirtualDMD(self.machine)

    def write_hw_rule(self, *args, **kwargs):
        pass

    def clear_hw_rule(self, sw_name):
        sw_num = self.machine.switches[sw_name].number

        for entry in list(self.hw_switch_rules.keys()):  # slice for copy
            if entry.startswith(
                    self.machine.switches.number(sw_num).name):
                del self.hw_switch_rules[entry]

    def i2c_write8(self, address, register, value):
        pass

    def i2c_read8(self, address, register):
        return None

    def i2c_read16(self, address, register):
        return None


class VirtualSwitch(object):
    """Represents a switch in a pinball machine used with virtual hardware."""
    def __init__(self, number):
        self.log = logging.getLogger('VirtualSwitch')
        self.number = number


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

    def disable(self):
        pass

    def enable(self):
        pass


class VirtualGI(GIPlatformInterface):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualGI')
        self.number = number
        self.current_brightness = 0

    def on(self, brightness):
        self.current_brightness = brightness

    def off(self):
        self.current_brightness = 0


class VirtualDriver(DriverPlatformInterface):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualDriver')
        self.number = number

    def __repr__(self):
        return "VirtualDriver.{}".format(self.number)

    def validate_driver_settings(self, **kwargs):
        return dict()

    def disable(self):
        pass

    def enable(self):
        pass

    def pulse(self, milliseconds=None):

        if milliseconds:
            return milliseconds
        else:
            return self.driver_settings['pulse_ms']

    def state(self):
        pass

    def tick(self):
        pass

    def reconfigure(self, polarity):
        pass


class VirtualDMD(object):
    def __init__(self, machine):
        pass

    def update(self, data):
        pass
