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

    def timer_initialize(self):
        """ Run this before the machine loop starts. I want to do it here so we
        don't need to check for initialization on each machine loop. (Or is
        this premature optimization?)

        """
        self.next_tick_time = time.time()

    def set_hw_rule(self, sw_name, sw_activity, coil_name=None,
                    coil_action_ms=0, pulse_ms=0, pwm_on=0, pwm_off=0, delay=0,
                    recycle_time=0, debounced=False, drive_now=False):
        """Writes a hardware rule to the controller.

        Args:
            sw_name: String name of the switch.
            sw_activity: String description of the switch activity this rule
                will be set for, either 'active' or 'inactive'.
            coil_name: String name of the coil.
            coil_action_ms: Total time in ms the coil should activate for.
            pulse_ms: How long in ms the coil should activate for. Default is 0.
            pwn_on: The 'on' portion, in ms of a pwm-based patter. Default is 0.
            pwm_off: The 'off' portion, in ms, of a pwm-based patter. Default is
                0.
            delay: The delay, in ms, the coil should wait before firing. Default
                is 0.
            recycle_time: How long the coil must be inactive, in ms, before it
                can be fired again via this rule. Default is 0.
            debounced: Boolean which specifies whether this coil should activate
                on a debounced or non-debounced switch change state. Default is
                False (non-debounced).
            drive_name: Boolean which controls whether the coil should activate
                immediately when this rule is applied if the switch currently in
                in the state set in this rule.

        Note that this method provides several convenience processing to convert
        the incoming parameters into a format that is more widely-used by
        hardware controls. It's intended that platform interfaces subclass
        `write_hw_rule()` instead of this method, though this method may be
        subclassed if you wish.

        """

        self.log.debug("Writing HW Rule to controller")

        sw = self.machine.switches[sw_name]  # todo make a nice error
        coil = self.machine.coils[coil_name]  # here too

        # convert sw_activity to hardware. (The game framework uses the terms
        # 'active' and 'inactive,' which take into consideration whether a
        # switch is normally open or normally closed. For example if we want to
        # fire a coil when a switch that is normally closed is activated, the
        # actual hw_rule we setup has to be when that switch opens, not closes.

        if self.machine.switches[sw_name].invert:
            sw_activity ^= 1

        self.write_hw_rule(sw, sw_activity, coil_action_ms, coil, pulse_ms,
                           pwm_on, pwm_off, delay, recycle_time, debounced,
                           drive_now)

    def write_hw_rule(sw, sw_activity, coil_action_ms, coil, pulse_ms, pwm_on,
                      pwm_off, delay, recycle_time, debounced, drive_now):
        """Subclass this method in a platform interface to write a hardware
        switch rule to the controller.

        Game programmers will typically use `set_hw_rule` instead of this method
        because `set_hw_rule` takes switch NC and NO settings into account, so
        it's a bit more convenient.

        """
        pass

    def clear_hw_rule(self, sw_name):
        """Subclass this method in a platform module to clear a hardware switch
        rule for this switch.

        Clearing a hardware rule means actions on this switch will no longer
        affect coils.

        Another way to think of this is that it 'disables' a hardware rule.
        This is what you'd use to disable flippers and autofire_coils during
        tilt, game over, etc.

        """
        pass

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
