"""Manages and tracks all the balls in a pinball machine."""
# ball_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

# todo new method to set live count. Like "I want live count of 3"

# todo new method to remove_live? And then if that gets to zero then we have a
# ball over?

import logging

from mpf.system.tasks import DelayManager


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

        # Properties:
        # self.num_balls_contained
        # self.num_balls_live
        # self.num_balls_desired_live

        self._num_balls_live = 0  # do not update this. Use the property
        self._num_balls_desired_live = 0  # do not update. Use the property
        self._num_balls_known = -999    # do not update. Use the property

        self.num_balls_in_transit = 0
        # Balls currently in transit from one ball device to another
        # Not currently implemented

        self.num_balls_missing = 0
        # Balls lost and/or not installed.

        self.flag_ball_search_in_progress = False
        #True if there's currently a ball search in progress.

        self.flag_no_ball_search = False
        #Ball search is enabled and disabled automatically based on whether
        #any balls are uncontained. Set this flag_no_ball_search to True if for
        #some reason you don't want the ball search to be enabled. BTW I can't
        #think of why you'd ever want this. The automatic stuff works great, and
        #you need to keep it enabled even after tilts and stuff. Maybe for some
        #kind of maintainance mode or something?

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)
        self.machine.events.add_handler('sw_ballLive',
                                        self.ball_live_hit)
        self.machine.events.add_handler('machine_reset_phase_2',
                                        self.reset)
        self.machine.events.add_handler('timer_tick',
                                        self._tick)

    @property
    def num_balls_contained(self):
        balls = 0
        for device in self.machine.balldevices:
            balls += device.num_balls_contained
            if balls > self._num_balls_known:
                self.num_balls_known = balls
        if balls < 0:
            return -999
        else:
            return balls
        # todo figure out how to do this with a generator

    @property
    def num_balls_live(self):
        return self._num_balls_live

    @num_balls_live.setter
    def num_balls_live(self, balls):
        """The number of balls that are actually live (i.e. loose and bouncing
        around) at this moment.

        This is not necessarily the same as the number of balls in play that the
        Game object tracks. For example during a game if the player shoots a
        ball into a ball device, there will be no live balls during that moment
        even though there is still a ball in play. And if the player tilts,
        there will be no balls in play but we'll still have balls live until
        they all roll into the drain.
        """

        prior_count = self._num_balls_live

        if balls > 0:
            self._num_balls_live = balls
            self.ball_search_schedule()
        else:
            self._num_balls_live = 0
            self.ball_search_disable()

        self.log.debug("New Live Ball Count: %s. (Prior count: %s)",
                       self._num_balls_live, prior_count)

        # todo add support for finding missing balls

    @property
    def num_balls_desired_live(self):
        return self._num_balls_desired_live

    @num_balls_desired_live.setter
    def num_balls_desired_live(self, balls):
        """How many balls the ball controller will try to keep live. If this
        number is ever greater than the number live, the ball controller will
        automatically add more live. If it's less, then the ball controller will
        not automatically eject a ball if it enters the drain device.
        """

        prior_count = self._num_balls_desired_live

        if balls > 0:
            self._num_balls_desired_live = balls
        else:
            self._num_balls_desired_live = 0

        self.log.debug("New Desired Live Ball Count: %s. (Prior count: %s)",
                       self._num_balls_desired_live, prior_count)

        # todo should we ensure that this value never exceed the number of balls
        # known? Or is that a crutch that will obscure programming errors?
        # I think we should do it but then log it as a warning.

    @property
    def num_balls_known(self):
        if self.num_balls_contained > self._num_balls_known:
            self._num_balls_known = self.num_balls_contained

        return self._num_balls_known

    @num_balls_known.setter
    def num_balls_known(self, balls):
        """How many balls the machine knows about. Could vary from the number
        of balls installed based on how many are *actually* in the machine, or
        to compensate for balls that are lost or stuck.
        """
        self._num_balls_known = balls

    def reset(self):
        """Resets the BallController.

        Current this just gets an initial count of the balls and sends all the
        balls to their 'home' position.
        """

        # If there are no ball devices, then the ball controller has no work to
        # do and will create errors, so we just abort.
        if not hasattr(self.machine, 'balldevices'):
            return

        self.num_balls_known = self.num_balls_contained

        # remove any old handlers
        self.machine.events.remove_handler(self._ball_add_live_handler)

        # add handlers to watch for balls ejected to the playfield
        for device in self.machine.balldevices:

            if device.config['confirm_eject_type'] != 'device':
                # This device ejects to the playfield

                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_eject_attempt',
                                                self._ball_add_live_handler)
                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_eject_failed',
                                                self._ball_remove_live_handler)
            if 'drain' in device.tags:  # device is used to drain balls from pf
                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_enter',
                                                self._ball_drained_handler)

            if not device.config['feeder_device']:
                # This device receives balls from the playfield
                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_enter',
                                                self._ball_remove_live_handler,
                                                priority=100)

        if 'Allow start with loose balls' not in self.machine.config['Game']:
            self.machine.config['Game']['Allow start with loose balls'] = False

        # todo where do we figure out balls missing?
        self.num_balls_live = 0
        self.num_balls_desired_live = 0

    def set_live_count(self, balls=None, from_tag='ball_add_live', device=None):
        """Tells the ball controller how many balls you want live."""
        self.log.debug("Setting desired live to: %s. (from_tag: %s, device: %s)",
                       balls, from_tag, device)
        self.log.debug("Previous desired live count: %s",
                       self.num_balls_desired_live)

        if balls is not None:
            self.num_balls_desired_live = balls

        if self.num_balls_desired_live <= self.num_balls_live:
            # no live balls to add
            return

        balls_to_add = self.num_balls_desired_live - self.num_balls_live

        # set which ball device we're working with
        if not device:
            device = self.machine.balldevices.items_tagged('ball_add_live')[0]
            self.log.debug("Will add ball from device: %s", device.name)
            # todo what if there isn't one? Need a clean error

        # can we eject from this device? Grab a ball if not
        if not device.num_balls_contained:
            self.log.debug("Asking device %s to stage 1 ball", device.name)
            device.num_balls_desired = 1  # this will stage a ball

        self.log.debug("Subtracting 1 ball from %s's desired count",
                       device.name)
        device.num_balls_desired -= balls_to_add

        # todo need to check how many balls ejectable this device has, and go
        # to another device if this one can't serve them all

    def add_live(self, balls=1, from_tag='ball_add_live', device=None):
        """Tells the ball controller to add a live ball.

        This method ensures you're not adding more balls live than you have
        available.

        By default it will try to add the ball(s) from devices tagged with
        'ball_add_live'.

        This is a convenience method which calls set_live_count()
        """
        self.log.debug("Received request to add %s live ball(s). Current "
                       "desired live:  %s", balls, self.num_balls_desired_live)
        if (self.num_balls_desired_live < self.num_balls_known and
                self.num_balls_desired_live + balls <= self.num_balls_known):

            self.set_live_count(self.num_balls_desired_live + balls, from_tag,
                                device)
            return True

        elif self.num_balls_desired_live + balls > self.num_balls_known:
            self.log.warning("Live ball request exceeds number of known balls")
            self.set_live_count(self.num_balls_known, from_tag, device)
            # should we return something here? I guess None is ok?

        else:
            self.log.debug("Cannot set new live ball count.")
            return False

    def stage_ball(self, tag='ball_add_live'):
        """Makes sure that ball devices with the tag passed have a ball."""

        for device in self.machine.balldevices.items_tagged(tag):
            device.num_balls_desired = 1

    def _tick(self):
        # ticks once per game loop. Tries to keep the number of live balls
        # matching the number of balls in play

        if self.num_balls_desired_live < 0:
            self.log.debug("Warning. num_balls_desired_live is negative. "
                          "Resetting to 0.")
            # todo found a lost ball??
            self.num_balls_desired_live = 0
            # todo change num_balls_desired_live to a property?

        if self.num_balls_live != self.num_balls_desired_live:
            self.log.debug("(tick) Current Balls Live: %s, Balls Desired: %s",
                           self.num_balls_live, self.num_balls_desired_live)
            self.set_live_count()

    def request_to_start_game(self):
        """Method registered for the *request_to_start_game* event.

        Checks to make sure that the balls are in all the right places and
        returns. If too many balls are missing (based on the config files 'Min
        Balls' setting), it will return False to reject the game start request.
        """
        self.log.debug("Received request to start game.")
        self.log.debug("Balls contained: %s, Min balls needed: %s",
                       self.num_balls_contained,
                       self.machine.config['Machine']['Min Balls'])
        if self.num_balls_contained < self.machine.config['Machine']['Min Balls']:
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
            count += device.get_status('num_balls_contained')

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
                if (target in device.tags):
                    device.num_balls_desired = device.config['ball_capacity']
                else:
                    device.num_balls_desired = 0

        elif antitarget:
            self.log.debug("Emptying balls from devices tagged '%s'",
                           antitarget)
            for device in self.machine.devices:
                if (target in device.tags):
                    device.num_balls_desired = 0
                else:
                    device.num_balls_desired = device.config['ball_capacity']

    def _ball_add_live_handler(self, balls):
        # Event handler which watches for device eject attempts to add
        # live balls

        if not balls:
            return

        # If our previous desired count was less or equal to our live count,
        # then this eject should increase the desired count. Why? Because
        # whatever caused this eject wants there to be more balls desired.

        # If the previous desired count was higher than this eject, then the
        # desired count shouldn't change, as these balls are fulfilling its
        # missing desired balls.

        # todo potential bug: What if prior desired was higher than prior live,
        # and we get a new live increase which takes it above the prior desired?
        # I *think* that should never happen since the ball controller would
        # try to launch a new ball if live fell below desired, but it's possible
        # we could get into this situation depending on staging times and stuff.

        # Let's log this as a warning for now and revisit this later.

        if ((self.num_balls_desired_live > self.num_balls_live) and
                balls > (self.num_balls_desired_live > self.num_balls_live)):
            self.log.warning("Ball add deficit warning. See note in "
                             "_ball_add_live_handler() in ball_controller.py")

        if self.num_balls_desired_live <= self.num_balls_live:
            self.num_balls_desired_live += balls

        self.num_balls_live += balls

        self.machine.events.post('ball_live_added',
                                 total_live=self.num_balls_live)

    def _ball_remove_live_handler(self, balls=1):
        # Event handler which watches for device ball entry events
        self.num_balls_live -= balls
        self.num_balls_desired_live -= balls

        self.machine.events.post('ball_live_removed',
                                 total_live=self.num_balls_live)

    def _ball_drained_handler(self, balls):
        # This is a special handler which is called when balls enter devices
        # tagged with drain. It posts a ball_drain event and automatically
        # decrements the desired_balls_live counter.
        self.log.debug("Ball Drain Handler. Previous desired live: %s. Will "
                      "decrement by 1 and post 'ball_drain' relay event.",
                      self.num_balls_desired_live)

        if not self.machine.tilted:
            self.num_balls_desired_live -= balls

            self.machine.events.post('ball_drain', ev_type='relay',
                                     callback=self._process_ball_drained,
                                     balls=balls)

        else:  # received a drain while tilted
            self.machine.events.post('tilted_ball_drain')

    def _process_ball_drained(self, balls=None, ev_result=None):
        # We don't need to do anything here because other modules (ball save,
        # the game, etc. should jump in and do whatever they need to do when a
        # ball is drained.
        pass

    def ball_live_hit(self):
        """A ball just hit a playfield switch.

        This means we have a ball loose on the playfield. (It doesn't
        necessarily mean that ball is "live," as this could happen as a ball
        rolls towards the drain after a tilt.)

        This method is mainly used to continuously push out the start time of
        the ball search. If this method is called when a ball search is in
        progress, it will end the it. (Since this method means we found the
        stuck ball.)

        Note you shouldn't have to call this method manually. The switch
        controller will do it automatically each time a switch tagged with
        'ball_live' has been activated.

        """
        if self.num_balls_live:
            self.ball_search_schedule()
        if self.flag_ball_search_in_progress:
            self.log.debug("Just got a live playfield hit during ball search, "
                           "so we're ending ball search.")
            self.ball_search_end()

    '''
     ____        _ _    _____                     _
    |  _ \      | | |  / ____|                   | |
    | |_) | __ _| | | | (___   ___  __ _ _ __ ___| |__
    |  _ < / _` | | |  \___ \ / _ \/ _` | '__/ __| '_ \
    | |_) | (_| | | |  ____) |  __/ (_| | | | (__| | | |
    |____/ \__,_|_|_| |_____/ \___|\__,_|_|  \___|_| |_|

    The following code interfaces with the ball search module (which actually
    performs the ball search). Here's the interface if you want to write your
    own:

    MPF will post events when it wants certain things to happen, like
    "ball_search_begin_1"
    "ball_search_begin_2"
    "ball_search_end"

    You can use the following methods from our machine controller. (These
    examples assume it's in your ball search module as self.machine.)

    self.machine.get_balldevice_status()

    Returns a dictionary of ball devices, with the device object as the key
    and the number of balls it contains at the value.

    If you want to access a balldevice, they're accessible via:
    self.machine.balldevices[<device>].x

    Valid methods incude eject()
    With force=True to force it to fire the eject coil even if it thinks
    there's no ball.

    # todo that should trigger an eject in progress which the game can use to
    figure out where the ball came from.

    This ball search module is not reponsible for "finding" a ball. It just
    manages all the actions that take place during a search. The MPF Ball
    Controller will "find" any balls that are knocked loose and will then
    cancel the search.

    If you create your own, you should receive the instance of the machine_
    controller as an init paramter.

    You can fire coils via self.machine.coils[<coilname>].pulse()
    '''

    # todo need to think about soft delay switches (flippers)

    def ball_search_schedule(self, secs=None, force=False):
        """Schedules a ball search to start. By default it will schedule it
        based on the time configured in the machine configuration files.

        If a ball search is already scheduled, this method will reset that
        schedule to the new time passed.

        Parameters
        ----------

        secs : into
            Schedules the ball search that many secs from now.

        force : bool
            Set True to force a ball search. Otherwise it will only schedule it
            if self.flag_no_ball_search is False

        """
        if self.machine.config['BallSearch']:
            if not self.flag_no_ball_search or force is True:
                if secs is not None:
                    start_ms = secs * 1000
                else:
                    start_ms = (self.machine.config['BallSearch']
                        ['Secs until ball search start'] * 1000)
                self.log.debug("Scheduling a ball search for %s secs from now",
                               start_ms / 1000.0)
                self.delay.reset("ball_search_start",
                                 ms=start_ms,
                                 callback=self.ball_search_begin)

    def ball_search_disable(self):
        """Disables ball search.

        Note this is used to prevent a future ball
        search from happening (like when all balls become contained.) This
        method is not used to cancel an existing ball search. (Use
        ball_search_end for that.)

        """
        self.log.debug("Disabling Ball Search")
        self.delay.remove('ball_search_start')

    def ball_search_begin(self, force=False):
        """Begin the ball search process"""
        if not self.flag_no_ball_search:
            self.log.debug("Received request to start ball search")
            # ball search should only start if we have uncontained balls
            if self.num_balls_live or force:
                # todo add audit
                self.flag_ball_search_in_progress = True
                self.machine.events.post("ball_search_begin_phase1")
                # todo set delay to start phase 2

            else:
                self.log.debug("We got request to start ball search, but we "
                               "have no balls uncontained. WTF??")

    def ball_search_failed(self):
        """Ball Search did not find the ball."""
        self.log.debug("Ball Search failed to find a ball. Disabling.")
        self.ball_search_end()
        self.ball_lost()

    def ball_search_end(self):
        """End the ball search, either because we found the ball or
        are giving up."""
        self.log.debug("Ball search ending")
        self.flag_ball_search_in_progress = False
        self.machine.events.post("ball_search_end")
        # todo cancel the delay for phase 2 if we had one

    def ball_lost(self):
        """Mark a ball as lost"""
        self.num_balls_known = self.num_balls_contained
        self.num_balls_missing = self.machine.config['Machine']\
            ['Balls Installed'] - self.num_balls_contained
        self.num_balls_live = 0
        # since desired count doesn't change, this will relaunch them
        self.log.debug("Ball(s) Marked Lost. Known: %s, Missing: %s",
                       self.num_balls_known, self.num_balls_missing)

        # todo audit balls lost

    def ball_found(self, num=1):
        """Used when a previously missing ball is found. Updates the balls
        known and balls missing variables.

        Parameters
        ----------

        num : int
            Specifies how many balls have been found. Default is 1.

        """
        self.log.debug("HEY!! We just found %s lost ball(s).", num)
        self.num_balls_known += num
        self.num_balls_missing -= num
        self.log.debug("New ball counts. Known: %s, Missing: %s",
                       self.num_balls_known, self.num_balls_missing)
        self.ball_update_all_counts()  # is this necessary? todo

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
