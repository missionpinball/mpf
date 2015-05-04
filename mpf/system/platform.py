""" Contains the parent classes Platform"""
# hardware.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import time


class Platform(object):
    """ Parent class for the machine's hardware controller.

    This is the class that each hardware controller (such as P-ROC or FAST)
    will subclass to talk to their hardware. If there is no physical hardware
    attached, then this class can be used on its own. (Many of the methods
    will do nothing and your game will work.)

    For example, the P-ROC HardwarePlatform class will have a Driver class
    with methods such as pulse() to fire a coil.

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
        self.features['hw_timer'] = True
        self.features['hw_rule_coil_delay'] = False
        self.features['variable_recycle_time'] = False

    def timer_initialize(self):
        """ Run this before the machine loop starts. I want to do it here so we
        don't need to check for initialization on each machine loop. (Or is
        this premature optimization?)

        """
        self.next_tick_time = time.time()

    def set_hw_rule(self,
                    sw_name,  # switch name
                    sw_activity,  # active or inactive?
                    coil_name=None,  # coil name
                    coil_action_ms=0,  # total time coil is active for
                    pulse_ms=0,  # ms to pulse the coil?
                    pwm_on=0,  # 'on' ms of a pwm-based patter
                    pwm_off=0,  # 'off' ms of a pwm-based patter
                    delay=0,  # delay before firing?
                    recycle_time=0,  # wait before firing again?
                    debounced=False,  # should coil wait for debounce?
                    drive_now=False,  # should rule check sw and fire coil now?
                    ):
        """Writes the hardware rule to the controller.

        """

        self.log.debug("Writing HW Rule to controller")

        sw = self.machine.switches[sw_name]  # todo make a nice error
        coil = self.machine.coils[coil_name]  # here too

        # convert sw_activity to hardware. (The game framework uses the terms
        # 'active' and 'inactive,' which take into consideration whether a
        # switch is normally open or normally closed. For example if we want to
        # fire a coil when a switch that is normally closed is activated, the
        # actual hw_rule we setup has to be when that switch opens, not closes.

        if sw_activity == 'active':
            sw_activity = 1
        elif sw_activity == 'inactive':
            sw_activity = 0
        else:
            raise ValueError('Invalid "switch activity" option for '
                             'AutofireCoil: %s. Valid options are "active"'
                             ' or "inactive".' % (sw_name))
        if self.machine.switches[sw_name].type == 'NC':
            sw_activity = sw_activity ^ 1  # bitwise invert

        self._do_set_hw_rule(sw, sw_activity, coil_action_ms, coil,
                            pulse_ms, pwm_on, pwm_off, delay, recycle_time,
                            debounced, drive_now)

    def clear_hw_rule(self, sw_name):
        """ Clears all the hardware switch rules for a switch, meaning those
        switch actions will no longer affect coils.

        Another way to think of this is that it 'disables' a hardware rule.
        This is what you'd use to disable flippers or bumpers during tilt, game
        over, etc.

        """
        self._do_clear_hw_rule(self.machine.switches[sw_name].number)

    def hw_loop(self):
        """Called once per game loop to read the platform hardware for any
        changes to any devices."""
        time.sleep(0.001)

    def verify_switches(self):
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
