"""Contrains the BallController class which manages and tracks all the balls in
a pinball machine."""
# ball_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

import logging

from mpf.system.tasks import DelayManager
from mpf.system.devices import Device, DeviceCollection
from mpf.devices.playfield import Playfield


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

        self.machine.playfield = None  # Configured in machine_init_phase_2

        self._num_balls_known = -999

        self.num_balls_missing = 0
        # Balls lost and/or not installed.

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)
        self.machine.events.add_handler('machine_reset_phase_2',
                                        self._initialize)
        self.machine.events.add_handler('machine_init_phase_2',
                                        self.create_playfield_device)

    @property
    def balls(self):
        balls = 0
        for device in self.machine.balldevices:
            balls += device.balls
            if balls > self._num_balls_known:
                self.num_balls_known = balls
        if balls < 0:
            return -999
        else:
            return balls
        # todo figure out how to do this with a generator

    @property
    def num_balls_known(self):
        if self.balls > self._num_balls_known:
            self._num_balls_known = self.balls

        return self._num_balls_known

    @num_balls_known.setter
    def num_balls_known(self, balls):
        """How many balls the machine knows about. Could vary from the number
        of balls installed based on how many are *actually* in the machine, or
        to compensate for balls that are lost or stuck.
        """
        self._num_balls_known = balls

    def create_playfield_device(self):
        """Creates the actual playfield ball device and assigns it to
        self.playfield.
        """
        if not hasattr(self.machine, 'balldevices'):
            self.machine.balldevices = DeviceCollection()

        self.machine.playfield = Playfield(self.machine, name='playfield',
                                           collection='balldevices')

    def _initialize(self):

        # If there are no ball devices, then the ball controller has no work to
        # do and will create errors, so we just abort.
        if not hasattr(self.machine, 'balldevices'):
            return

        self.num_balls_known = self.balls

        for device in self.machine.balldevices:
            if 'drain' in device.tags:  # device is used to drain balls from pf
                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_enter',
                                                self._ball_drained_handler)

        # todo
        if 'Allow start with loose balls' not in self.machine.config['Game']:
            self.machine.config['Game']['Allow start with loose balls'] = False

    def request_to_start_game(self):
        """Method registered for the *request_to_start_game* event.

        Checks to make sure that the balls are in all the right places and
        returns. If too many balls are missing (based on the config files 'Min
        Balls' setting), it will return False to reject the game start request.
        """
        self.log.debug("Received request to start game.")
        self.log.debug("Balls contained: %s, Min balls needed: %s",
                       self.balls,
                       self.machine.config['Machine']['Min Balls'])
        if self.balls < self.machine.config['Machine']['Min Balls']:
            self.log.debug("BallController denies game start. Not enough balls")
            return False

        if self.machine.config['Game']['Allow start with loose balls']:
            return

        elif not self.are_balls_gathered(['home', 'trough']):
            self.gather_balls('home')
            self.log.debug("BallController denies game start. Balls are not in"
                           " their home positions.")
            return False

    def are_balls_gathered(self, target=['home', 'trough']):
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
            target = [target]

        count = 0
        devices = set()

        for tag in target:
            for device in self.machine.balldevices.items_tagged(tag):
                devices.add(device)

        if len(devices) == 0:
            # didn't find any devices matching that tag, so we return True
            return True

        for device in devices:
            count += device.get_status('balls')

        if count == self.machine.ball_controller.num_balls_known:
            self.log.debug("Yes, all balls are gathered")
            return True
        else:
            self.log.debug("No, all balls are not gathered")
            return False

    def gather_balls(self, target='home', antitarget=None):
        """Used to ensure that all balls are in (or not in) ball devices with
        the tag you pass.

        Typically this would be used after a game ends, or when the machine is
        reset or first starts up, to ensure that all balls are in devices
        tagged with 'home'.

        Args:
            target: A string of the tag name of the ball devices you want all
                the balls to end up in. Default is 'home'.
            antitarget: The opposite of target. Will eject all balls from
                all devices with the string you pass. Default is None.

        Note you can't pass both a target and antitarget in the same call. (If
        you do it will just use the target and ignore the antitarget.)

        TODO: Add support to actually move balls into position. e.g. STTNG, the
        lock at the top of the playfield wants to hold a ball before a game
        starts, so when a game ends the machine will auto eject one from the
        plunger with the diverter set so it's held in the rear lock.
        """

        if not antitarget:
            # todo do we add the option of making the target a list?
            self.log.debug("Gathering all balls to devices tagged '%s'",
                           target)
            for device in self.machine.balldevices:
                if target not in device.tags and device.balls > 0:
                    device.eject_all()

        elif antitarget:
            self.log.debug("Emptying balls from devices tagged '%s'",
                           antitarget)
            for device in self.machine.devices:
                if target in device.tags and device.balls > 0:
                    device.eject(balls=device.balls)

    def _ball_drained_handler(self, balls):
        self.machine.events.post_relay('ball_drain',
                                       callback=self._process_ball_drained,
                                       balls=balls)

        # What happens if the ball enters the trough but the ball_add_live
        # event hasn't confirmed its eject? todo

    def _process_ball_drained(self, balls=None, ev_result=None):
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
