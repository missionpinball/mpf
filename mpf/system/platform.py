""" Contains the parent classes Platform"""
# platform.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import time



class Platform(object):
    """Parent class for the a hardware platform interface.

    Args:
        machine: The main ``MachineController`` instance.

    This is the class that each hardware controller (such as P-ROC or FAST)
    will subclass to talk to their hardware.

    """
    def __init__(self, machine):
        self.machine = machine
        self.HZ = None
        self.secs_per_tick = None
        self.next_tick_time = None
        self.features = {}
        self.hw_switch_rules = {}

        # Set default platform features. Each platform interface can change
        # these to notify the framework of the specific features it supports.
        self.features['max_pulse'] = 255
        self.features['hw_timer'] = False
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False

        from mpf.platform.snux import Snux
        self.driver_overlay = Snux(self.machine)

    def timer_initialize(self):
        """ Run this before the machine loop starts. I want to do it here so we
        don't need to check for initialization on each machine loop. (Or is
        this premature optimization?)

        """
        self.next_tick_time = time.time()

    def set_hw_rule(self, sw_name, sw_activity, driver_name, driver_action,
                    disable_on_release=True, drive_now=False,
                    **driver_settings_overrides):
        """Writes a hardware rule to the controller.

        Args:
            sw_name: String name of the switch.
            sw_activity: Int representing the switch state this rule will be set
                for. 1 is active, 0 is inactive.
            driver_name: String name of the driver.
            driver_action: String 'pulse', 'hold', or 'disable' which describe
                what action will be applied to this driver
            debounced: Boolean which specifies whether this coil should activate
                on a debounced or non-debounced switch change state. Default is
                False (non-debounced).
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

        switch_obj = self.machine.switches[sw_name]  # todo make a nice error
        driver_obj = self.machine.coils[driver_name]  # here too

        if self.machine.switches[sw_name].invert:
            sw_activity ^= 1

        self.write_hw_rule(switch_obj, sw_activity, driver_obj, driver_action,
                           disable_on_release, drive_now,
                           **driver_settings_overrides)

    def write_hw_rule(self, switch_obj, sw_activity, driver_obj, driver_action,
                      disable_on_release, drive_now,
                      **driver_settings_overrides):
        """Subclass this method in a platform interface to write a hardware
        switch rule to the controller.

        Game programmers will typically use `set_hw_rule` instead of this method
        because `set_hw_rule` takes switch NC and NO settings into account, so
        it's a bit more convenient.

        """
        raise NotImplementedError

    def clear_hw_rule(self, sw_name):
        """Subclass this method in a platform module to clear a hardware switch
        rule for this switch.

        Clearing a hardware rule means actions on this switch will no longer
        affect coils.

        Another way to think of this is that it 'disables' a hardware rule.
        This is what you'd use to disable flippers and autofire_coils during
        tilt, game over, etc.

        """
        raise NotImplementedError

    def tick(self):
        """Subclass this method in a platform module to perform periodic updates
        to the platform hardware, e.g. reading switches, sending driver or
        light updates, etc.

        If you want to use this method and let MPF control the machine's run
        loop, set `self.features['hw_timer'] = False`.

        This method is only used when MPF controls the game loop. Each platform
        interface either needs to implement this method or the `run_loop`
        method.

        This method will be called every 1ms.

        """
        pass

    def run_loop(self):
        """Subclass this method in a platform module if the platform will
        control the run loop rather than MPF controlling it.

        If you want to use this method and let your platform control the
        machine's run loop, set `self.features['hw_timer'] = True`.

        If your platform controls the loop, it should call
        `self.machine.timer_tick()` periodically based on the `self.machine.HZ`
        rate.

        Also the loop should continue running until `self.machine.done` is True.
        For example, it could run in `while not self.machine.done:` loop.

        Your loop can call `self.machine.switch_controller.process_switch()` if
        any switch events come in "off cycle", but the timer_tick should be
        called consistently.

        This loop can safely block. If the call to the hardware does not block,
        there should be a small pause in the loop (e.g. `time.sleep(.001)` to
        prevent 100% CPU utilization.)

        """
        pass

    def get_hw_switch_states(self):
        """Subclass this method in a platform module to return the hardware
        states of all the switches on that platform.
        of a switch.

        This method should return a dict with the switch numbers as keys and the
        hardware state of the switches as values. (0 = inactive, 1 = active)
        This method should not compensate for NO or NC status, rather, it
        should return the raw hardware states of the switches.

        """
        pass

    def configure_driver(self, config, device_type='coil'):
        """Subclass this method in a platform module to configure a driver.

        This method should return a reference to the driver's platform interface
        object which will be called to access the hardware.

        """
        pass

    def configure_switch(self, config):
        """Subclass this method in a platform module to configure a switch.

        This method should return a reference to the switch's platform interface
        object which will be called to access the hardware.

        """
        pass

    def configure_led(self, config):
        """Subclass this method in a platform module to configure an LED.

        This method should return a reference to the LED's platform interface
        object which will be called to access the hardware.

        """
        pass

    def configure_gi(self, config):
        """Subclass this method in a platform module to configure a GI string.

        This method should return a reference to the GI string's platform
        interface object which will be called to access the hardware.

        """
        pass

    def configure_matrixlight(self, config):
        """Subclass this method in a platform module to configure a matrix
        light.

        This method should return a reference to the matrix lights's platform
        interface object which will be called to access the hardware.

        """
        pass

    def configure_dmd(self):
        """Subclass this method in a platform module to configure the DMD.

        This method should return a reference to the DMD's platform interface
        object which will be called to access the hardware.

        """
        pass


class DriverOverlay(object):

    @classmethod
    def write_hw_rule(cls, func):

        def _decorated_write_hw_rule(self, *args, **kwargs):
            print "decorated driver"
            print self
            print args
            print kwargs
            print
            print func
            print

            if self.driver_overlay:
                self.driver_overlay.write_hw_rule(*args, **kwargs)
            else:
                func(*args, **kwargs)

        return _decorated_write_hw_rule



# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
