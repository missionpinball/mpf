"""Contains template code for a new hardware platform interface for MPF. You
can use this as the starting point for your own platform.

Note that if you create your own platform interface, we will be happy to add it
to the MPF package. That way we can help maintain it moving forward.

You can search-and-replace the word "template" (not case sensitive) with the
name of your own platform.

"""

import logging
from mpf.core.platform import Platform
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.rgb_led_platform_interface import RGBLEDPlatformInterface
from mpf.platforms.interfaces.matrix_light_platform_interface import MatrixLightPlatformInterface
from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface


# you might have to add additional imports here for modules you need for your
# platform


class HardwarePlatform(Platform):
    """This is the base class for your hardware platform. Note that at this
    time, this class *must* be called HardwarePlatform."""

    def __init__(self, machine):
        super().__init__(machine)
        self.log = logging.getLogger("Template Platform")
        self.log.debug("Configuring template hardware interface.")
        self.initial_states_sent = False

        # The following "features" are supposed to be constants that you can
        # use to define was is or is not in your own platform. However they
        # have not been implemented at this time. So for now just keep them
        # as-is below and we'll deal with them in some future version of MPF.
        self.features['max_pulse'] = 255
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False
        self.features['variable_debounce_time'] = False

        # Make the platform features available to everyone
        self.machine.config['platform'] = self.features

    def __repr__(self):
        """String name you'd like to show up in logs and stuff when a
        reference to this platform is printed."""
        return '<Platform.Template>'

    def configure_driver(self, config, device_type='coil'):
        """This method is called once per driver when MPF is starting up. It
        passes the config for the driver and returns a hardware driver object
        that can be used to control the driver.

        Args:
            config: A dict of configuration key/value settings that will be
                passed on to your driver class to create an instance of your
                driver. These can be whatever you want--whatever you need to
                setup a driver.
            device_type: String name of the type of MPF device that's being
                configured. This is needed since some platforms (like Williams
                WPC) use "drivers" to control coils, lights, GI, flashers, etc.
                Whether you need to act on this is up to you. Just know that
                when MPF calls this method, it will pass the config dict for
                this device as well as a string name of what type of device
                it's trying to setup.

        Returns:
            driver object, config number. The driver object that is returned
            is a your hardware driver that should have driver-like methods like
            pulse(), enable(), disable(), etc. It should already be mapped to
            the proper driver so it can be called directly like driver.pulse().
            Different types of drivers (e.g. coils vs. flashers) will have
            different methods available. (Keep reading for details.)

            The config number that's returned isn't really used. It's just
            stored by MPF in case this driver needs to be referenced by number
            in the future.

        """

        # In this example, we're passing the complete config dictionary to the
        # TemplateDriver constructor so it can set itself up as needed. You
        # might choose to only pass certain k/v pairs, or whatever else you
        # want.
        driver = TemplateDriver(config['number'])

        driver.driver_settings = config
        driver.driver_settings['pulse_ms'] = 30

        return driver, config['number']

    def configure_switch(self, config):
        """Called once per switch when MPF boots. It's used to setup the
        hardware switch interface.

        The main MPF loop will expect to receive notifications of switch
        changes in the main platform.tick() events. It will not poll every
        single switch. (If you need that behavior, you need to write it in the
        tick() method.

        Note: This method is similar to the configure_driver() method.

        Args:
            config: A dict of configuration key/value settings that will be
                passed on to your switch class to create an instance of your
                switch. These can be whatever you want--whatever you need to
                setup a switch.

        Returns:
            A reference to the instance of your harware switch class. This will
            be queried later to read the state of the switch.

        """

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

                initial_active_switches = [self.machine.switches[x].number for
                                           x in
                                           Util.string_to_list(
                                                   self.machine.config[
                                                       'virtual_platform_start_active_switches'])]

                for k in self.hw_switches:
                    if k in initial_active_switches:
                        self.hw_switches[k] ^= 1

            self.initial_states_sent = True

        else:
            switches = [x for x in self.machine.switches if x.platform == self]

            for switch in switches:
                self.hw_switches[switch.number] = switch.state ^ switch.invert

        return self.hw_switches

    def configure_accelerometer(self, device, number, use_high_pass):
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
        del address
        del register
        return None

    def i2c_read16(self, address, register):
        del address
        del register
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

    def on(self, brightness=255):
        pass

    def off(self):
        pass


class VirtualLED(RGBLEDPlatformInterface):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualLED')
        self.number = number

    def color(self, color):
        # self.log.debug("Setting color: %s, fade: %s, comp: %s",
        #               color, fade_ms, brightness_compensation)
        pass

    def disable(self):
        pass

    def enable(self):
        pass


class VirtualGI(GIPlatformInterface):
    def __init__(self, number):
        self.log = logging.getLogger('VirtualGI')
        self.number = number

    def on(self, brightness=255):
        pass

    def off(self):
        pass


class TemplateDriver(DriverPlatformInterface):
    """The base class for a hardware driver on your platform. Several methods
    are required, including:

    disable()
    enable()
    pulse()

    The following are optional:
    state()
    tick()
    reconfigure()

    """

    def __init__(self, number):
        self.log = logging.getLogger('VirtualDriver')
        self.number = number

    def __repr__(self):
        return "VirtualDriver.{}".format(self.number)

    def disable(self):
        pass

    def enable(self):
        """Enables this driver, which means it's held "on" indefinitely until
        it's explicitly disabled.

        """
        # The actual code here will be the call to your library or whatever
        # that physically enables this driver. Remember this object is just for
        # this single driver, so it's up to you to set or save whatever you
        # nned in __init__() so that you know which driver to call from this
        # instance of the class.

        # for example (pseudocode):

        # self.serial_connection.send(self.number, 1)

        # or

        # self.my_driver(self.driver_number, command='enable', time=-1)

        pass

    def pulse(self, milliseconds=None):
        """Pulses this driver for a pre-determined amount of time, after which
        this driver is turned off automatically. Note that on most platforms,
        pulse times are a max of 255ms. (Beyond that MPF will send separate
        enable() and disable() commands.

        Args:
            milliseconds: The number of ms to pulse this driver for. You should
                raise a ValueError if the value is out of range for your
                platform. If this value is None, you should pulse this driver
                with a default setting. You can set the default in the driver
                config via your __init__() method, or you can pick some default
                that's hard coded.

        Returns:
            A integer of the actual time this driver is going to be pulsed for.
            MPF uses this for timing in certain situations to make sure too
            many drivers aren't activated at once.

        """
        if not milliseconds:
            milliseconds = self.driver_settings['pulse_ms']

        # do the actual hardware pulse... whatever that looks like for your
        # platform

        return milliseconds

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
