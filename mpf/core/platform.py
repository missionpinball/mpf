""" Contains the parent classes Platform"""


class BasePlatform(object):
    def __init__(self, machine):
        self.machine = machine
        self.HZ = None
        self.secs_per_tick = None
        self.next_tick_time = None
        self.features = {}
        self.log = None

        # Set default platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['has_dmd'] = False
        self.features['has_accelerometers'] = False
        self.features['has_i2c'] = False
        self.features['has_servos'] = False
        self.features['has_matrix_lights'] = False
        self.features['has_gis'] = False
        self.features['has_switches'] = False
        self.features['has_drivers'] = False

    def initialize(self):
        pass

    def timer_initialize(self):
        """ Run this before the machine loop starts. I want to do it here so we
        don't need to check for initialization on each machine loop. (Or is
        this premature optimization?)

        """
        self.next_tick_time = self.machine.clock.get_time()

    def tick(self, dt):
        """Subclass this method in a platform module to perform periodic updates
        to the platform hardware, e.g. reading switches, sending driver or
        light updates, etc.

        """
        pass

    def stop(self):
        """Subclass this method in the platform module if you need to perform
        any actions to gracefully stop the platform interface.

        This could do things like reseting it, stopping events, etc.

        This method will be called when MPF stops, including when an MPF thread
        crashes.

        """
        pass


class DmdPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_dmd'] = True

    def configure_dmd(self):
        """Subclass this method in a platform module to configure the DMD.

        This method should return a reference to the DMD's platform interface
        object which will be called to access the hardware.

        """
        raise NotImplementedError


class AccelerometerPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_accelerometers'] = True

    def configure_accelerometer(self, device, number, use_high_pass):
        raise NotImplementedError


class I2cPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_i2c'] = True

    def i2c_write8(self, address, register, value):
        raise NotImplementedError

    def i2c_read8(self, address, register):
        raise NotImplementedError

    def i2c_read16(self, address, register):
        raise NotImplementedError


class ServoPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_servos'] = True

    def servo_go_to_position(self, number, position):
        raise NotImplementedError


class MatrixLightsPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_matrix_lights'] = True

    def configure_matrixlight(self, config):
        """Subclass this method in a platform module to configure a matrix
        light.

        This method should return a reference to the matrix lights's platform
        interface object which will be called to access the hardware.

        """
        raise NotImplementedError


class GiPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_gis'] = True

    def configure_gi(self, config):
        """Subclass this method in a platform module to configure a GI string.

        This method should return a reference to the GI string's platform
        interface object which will be called to access the hardware.

        """
        raise NotImplementedError


class LedPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_gis'] = True

    def configure_led(self, config):
        """Subclass this method in a platform module to configure an LED.

        This method should return a reference to the LED's platform interface
        object which will be called to access the hardware.

        """
        raise NotImplementedError


class SwitchPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.features['has_switches'] = True

    def configure_switch(self, config):
        """Subclass this method in a platform module to configure a switch.

        This method should return a reference to the switch's platform interface
        object which will be called to access the hardware.

        """
        raise NotImplementedError

    def get_hw_switch_states(self):
        """Subclass this method in a platform module to return the hardware
        states of all the switches on that platform.
        of a switch.

        This method should return a dict with the switch numbers as keys and the
        hardware state of the switches as values. (0 = inactive, 1 = active)
        This method should not compensate for NO or NC status, rather, it
        should return the raw hardware states of the switches.

        """
        raise NotImplementedError


class DriverPlatform(BasePlatform):
    def __init__(self, machine):
        super().__init__(machine)
        self.driver_overlay = None

        # Set default platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['has_drivers'] = True
        self.features['max_pulse'] = 255
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False

        # todo change this to be dynamic for any overlay
        if self.machine.config['hardware']['driverboards'] == 'snux':
            from mpf.platforms.snux import Snux
            self.driver_overlay = Snux(self.machine, self)
            self.machine.config['hardware']['driverboards'] = 'wpc'

    def initialize(self):
        super().initialize()
        if self.driver_overlay:  # can't use try since it could swallow errors
            self.driver_overlay.initialize()

    def configure_driver(self, config):
        """Subclass this method in a platform module to configure a driver.

        This method should return a reference to the driver's platform interface
        object which will be called to access the hardware.

        """
        raise NotImplementedError

    # pylint: disable-msg=too-many-arguments
    def set_hw_rule(self, sw_name, sw_activity, driver_name, driver_action,
                    disable_on_release=True, drive_now=False, switch_obj=None,
                    **driver_settings_overrides):
        """Writes a hardware rule to the controller.

        Args:
            sw_name: String name of the switch.
            sw_activity: Int representing the switch state this rule will be set
                for. 1 is active, 0 is inactive.
            driver_name: String name of the driver.
            driver_action: String 'pulse', 'hold', or 'disable' which describe
                what action will be applied to this driver
            disable_on_release: If set to True, the driver will disable when the
                switch is released
            drive_now: Boolean which controls whether the coil should activate
                immediately when this rule is applied if the switch currently in
                in the state set in this rule.
            **driver_settings_overrides: Platform-specific settings

        Note that this method provides several convenience processing to convert
        the incoming parameters into a format that is more widely-used by
        hardware controls. It's intended that platform interfaces subclass
        `write_hw_rule()` instead of this method, though this method may be
        subclassed if you wish.

        """
        self.log.debug("Writing HW Rule to controller")

        if not switch_obj:
            switch_obj = self.machine.switches[sw_name]  # todo make a nice error
        driver_obj = self.machine.coils[driver_name]  # here too

        if switch_obj.invert:
            sw_activity ^= 1

        self.write_hw_rule(switch_obj, sw_activity, driver_obj, driver_action,
                           disable_on_release, drive_now,
                           **driver_settings_overrides)

    def clear_hw_rule(self, switch, coil):
        """Subclass this method in a platform module to clear a hardware switch
        rule for this switch.

        Clearing a hardware rule means actions on this switch will no longer
        affect coils.

        Another way to think of this is that it 'disables' a hardware rule.
        This is what you'd use to disable flippers and autofire_coils during
        tilt, game over, etc.

        """
        raise NotImplementedError

    def get_coil_config_section(self):
        return None

    def get_switch_config_section(self):
        return None

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        raise NotImplementedError

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        raise NotImplementedError

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        raise NotImplementedError
