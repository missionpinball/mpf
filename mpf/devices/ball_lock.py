""" Contains the BallLock device class."""
# ball_lock.py
# Mission Pinball Framework
# MPF is written by Brian Madden & Gabe Knuth
# This module was originally written by Jan Kantert
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf


import logging
from mpf.system.device import Device
from mpf.system.config import Config
from collections import deque

class BallLock(Device):

    config_section = 'ball_locks'
    collection = 'ball_locks'
    class_label = 'ball_lock'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super(BallLock, self).__init__(machine, name, config, collection,
                                       validate=validate)

        # initialise variables
        self.balls_locked = 0
        self.lock_queue = deque()

        # let ball devices initialise first
        self.machine.events.add_handler('init_phase_3',
                                        self._initialize)

    def _initialize(self):
        # load lock_devices

        self.lock_devices = []
        self.enabled = False
        for device in self.config['lock_devices']:
            self.lock_devices.append(device)

        self.source_playfield = self.config['source_playfield']

    def enable(self, **kwargs):
        """ Enables the lock. If the lock is not enabled, no balls will be
        locked.
        """
        self.log.debug("Enabling...")
        if not self.enabled:
            self._register_handlers()
        self.enabled = True

    def disable(self, **kwargs):
        """ Disables the lock. If the lock is not enabled, no balls will be
        locked.
        """
        self.log.debug("Disabling...")
        self._unregister_handlers()
        self.enabled = False

    def reset(self, **kwargs):
        """Resets the lock. Will release locked balls. Device will status will
        stay the same (enabled/disabled)
        """
        self.release_all_balls()

    def release_all_balls(self):
        self.release_balls(self.balls_locked)

    def release_balls(self, balls_to_release):
        """Release all balls and return the actual amount of balls released.
        """
        if len(self.lock_queue) == 0:
            return 0

        remaining_balls_to_release = balls_to_release

        self.log.debug("Releasing up to %s balls from lock", balls_to_release)
        balls_released = 0
        while len(self.lock_queue) > 0:
            device, balls_locked = self.lock_queue.pop()
            balls = balls_locked
            balls_in_device = device.count_balls(stealth=True)
            if balls > balls_in_device:
                balls = balls_in_device

            if balls > remaining_balls_to_release:
                self.lock_queue.append((device, balls_locked - remaining_balls_to_release))
                balls = remaining_balls_to_release

            device.eject(balls=balls)
            balls_released += balls
            remaining_balls_to_release -= balls
            if remaining_balls_to_release <= 0:
                break

        if balls_released > 0:
            self.machine.events.post('ball_lock_' + self.name + '_balls_released',
                                     balls_released=balls_released)

        self.balls_locked -= balls_released
        return balls_released

    def _register_handlers(self):
        # register on ball_enter of lock_devices
        for device in self.lock_devices:
            self.machine.events.add_handler('balldevice_' + device.name + '_ball_enter',
                                            self._lock_ball, device=device)

    def _unregister_handlers(self):
        # unregister ball_enter handlers
        self.machine.events.remove_handler(self._lock_ball)

    # return true if lock is full
    def is_full(self):
        return self.remaining_space_in_lock() == 0

    # return the remaining capacity of the lock
    def remaining_space_in_lock(self):
        balls = self.config['balls_to_lock'] - self.balls_locked
        if balls < 0:
             balls = 0
        return balls

    # callback for _ball_enter event of lock_devices
    def _lock_ball(self, device, balls, **kwargs):
        # if full do not take any balls
        if self.is_full():
            self.log.debug("Cannot lock balls. Lock is full.", balls_to_lock)
            return {'balls': balls}

        # if there are no balls do not claim anything
        if balls <= 0:
            return {'balls': balls}

        capacity = self.remaining_space_in_lock()
        # take ball up to capacity limit
        if balls > capacity:
            balls_to_lock = capacity
        else:
            balls_to_lock = balls

        self.balls_locked += balls_to_lock
        self.log.debug("Locked %s balls", balls_to_lock)

        # post event for ball capture
        self.machine.events.post('ball_lock_' + self.name + '_locked_ball',
                                  balls_locked=balls_to_lock,
                                  total_balls_locked=self.balls_locked)

        # check if we are full now and post event if yes
        if self.is_full():
            self.machine.events.post('ball_lock_' + self.name + '_full',
                                     balls=self.balls_locked)

        self.lock_queue.append((device, balls))

        # schedule eject of new balls
        self.request_new_balls(balls_to_lock)

        return {'balls': balls - balls_to_lock}

    def request_new_balls(self, balls):
        self.source_playfield.add_ball(balls=balls)


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
