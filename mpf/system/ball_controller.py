"""Contrains the BallController class which manages and tracks all the balls in
a pinball machine."""
# ball_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

import logging

from mpf.system.tasks import DelayManager
from mpf.system.config import Config


class BallController(object):
    """Base class for the Ball Controller which is used to keep track of all
    the balls in a pinball machine.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """
    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("BallController")
        self.log.debug("Loading the BallController")
        self.delay = DelayManager()

        self.game = None

        self._num_balls_known = -999

        self.num_balls_missing = 0
        # Balls lost and/or not installed.

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)
        self.machine.events.add_handler('machine_reset_phase_2',
                                        self._initialize)
        # self.machine.events.add_handler('init_phase_2',
        #                                 self.create_playfield_device, 2)

    def _count_balls(self):
        self.log.debug("Counting Balls")
        balls = 0
        for device in self.machine.ball_devices:
            if not device._count_consistent:
                return -999
            self.log.debug("Found %s ball(s) in %s", device.balls, device.name)
            balls += device.balls

        if balls > self._num_balls_known:
            self.log.debug("Setting known balls to %s", balls)
            self.num_balls_known = balls

        if balls < 0:
            return -999
        else:
            return balls
        # todo figure out how to do this with a generator

    @property
    def num_balls_known(self):
        self._update_num_balls_known()

        return self._num_balls_known

    def _update_num_balls_known(self):
        balls = self._count_balls() 

        if balls < 0:
            self.delay.add(callback=self._update_num_balls_known, ms=10)

        if balls > self._num_balls_known:
            self._num_balls_known = balls


    @num_balls_known.setter
    def num_balls_known(self, balls):
        """How many balls the machine knows about. Could vary from the number
        of balls installed based on how many are *actually* in the machine, or
        to compensate for balls that are lost or stuck.
        """
        self._num_balls_known = balls

    def _initialize(self):

        # If there are no ball devices, then the ball controller has no work to
        # do and will create errors, so we just abort.
        if not hasattr(self.machine, 'ball_devices'):
            return

        self._update_num_balls_known()

        for device in self.machine.ball_devices:
            if 'drain' in device.tags:  # device is used to drain balls from pf
                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_enter',
                                                self._ball_drained_handler)

        # todo
        if 'Allow start with loose balls' not in self.machine.config['game']:
            self.machine.config['game']['Allow start with loose balls'] = False

    def request_to_start_game(self):
        """Method registered for the *request_to_start_game* event.

        Checks to make sure that the balls are in all the right places and
        returns. If too many balls are missing (based on the config files 'Min
        Balls' setting), it will return False to reject the game start request.
        """
        balls = self._count_balls()
        self.log.debug("Received request to start game.")
        self.log.debug("Balls contained: %s, Min balls needed: %s",
                       balls,
                       self.machine.config['machine']['min_balls'])
        if balls < self.machine.config['machine']['min_balls']:
            self.log.warning("BallController denies game start. Not enough "
                             "balls")
            return False

        if self.machine.config['game']['Allow start with loose balls']:
            return

        elif not self.are_balls_collected(['home', 'trough']):
            self.collect_balls('home')
            self.log.warning("BallController denies game start. Balls are not "
                             "in their home positions.")
            return False

    def are_balls_collected(self, target=['home', 'trough'], antitarget=None):
        """Checks to see if all the balls are contained in devices tagged with
        the parameter that was passed.

        Note if you pass a target that's not used in any ball devices, this
        method will return True. (Because you're asking if all balls are
        nowhere, and they always are. :)

        Args:
            target: String value of the tag you'd like to check. Default is
            'home'
        """

        self.log.debug("Checking to see if all the balls are in devices tagged"
                       " with '%s'", target)

        if type(target) is str:
            target = Config.string_to_list(target)

        count = 0
        devices = set()

        for tag in target:
            for device in self.machine.ball_devices.items_tagged(tag):
                devices.add(device)

        if len(devices) == 0:
            # didn't find any devices matching that tag, so we return True
            return True

        for device in devices:
            count += device.get_status('balls')
            self.log.debug('Found %s ball(s) in %s. Found %s total',
                           device.get_status('balls'), device.name, count)

        if count == self.machine.ball_controller.num_balls_known:
            self.log.debug("Yes, all balls are collected")
            return True
        else:
            self.log.debug("No, all balls are not collected. Balls Counted: %s. "
                           "Total balls known: %s", count,
                           self.machine.ball_controller.num_balls_known)
            return False

    def collect_balls(self, target='home, trough'):
        """Used to ensure that all balls are in contained in ball devices with
        the tag or list of tags you pass.

        Typically this would be used after a game ends, or when the machine is
        reset or first starts up, to ensure that all balls are in devices
        tagged with 'home' and/or 'trough'.

        Args:
            target: A string of the tag name or a list of tags names of the
                ball devices you want all the balls to end up in. Default is
                ['home', 'trough'].

        """
        # I'm embarrassed at how ugly this code is. But meh, it works...

        tag_list = Config.string_to_list(target)

        self.log.debug("Collecting all balls to devices with tags '%s'",
                       tag_list)

        target_devices = set()
        source_devices = set()
        balls_to_collect = False

        for tag in tag_list:
            for device in self.machine.ball_devices.items_tagged(tag):
                target_devices.add(device)

        for device in self.machine.ball_devices:
            if device not in target_devices:
                if device.balls:
                    source_devices.add(device)
                    balls_to_collect = True

        self.log.debug("Ejecting all balls from: %s", source_devices)

        if balls_to_collect:
            self.machine.events.post('collecting_balls')

            for device in target_devices:
                self.machine.events.replace_handler(
                    'balldevice_{}_ball_enter'.format(device.name),
                    self._collecting_balls_entered_callback,
                    target=target)

            for device in source_devices:
                device.eject_all()
        else:
            self.log.debug("All balls are collected")

    def _collecting_balls_entered_callback(self, target, balls, **kwargs):
        if self.are_balls_collected(target=target):
            self._collecting_balls_complete()

        return {'balls': balls}

    def _collecting_balls_complete(self):
        self.machine.events.remove_handler(self._collecting_balls_complete)
        self.machine.events.post('collecting_balls_complete')

    def _ball_drained_handler(self, balls, device, **kwargs):
        self.machine.events.post_relay('ball_drain',
                                       callback=self._process_ball_drained,
                                       device=device,
                                       balls=balls)

        # What happens if the ball enters the trough but the ball_add_live
        # event hasn't confirmed its eject? todo

    def _process_ball_drained(self, balls=None, ev_result=None, **kwargs):
        # We don't need to do anything here because other modules (ball save,
        # the game, etc. should jump in and do whatever they need to do when a
        # ball is drained.
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
