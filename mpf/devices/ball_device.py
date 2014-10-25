""" Contains the base class for ball devices."""
# ball_device.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.tasks import DelayManager
from mpf.system.devices import Device
from mpf.system.timing import Timing


class BallDevice(Device):
    """Base class for a 'Ball Device' in a pinball machine.

    A ball device  is anything that can hold one or more balls, such as a
    trough, an eject hole, a VUK, a catapult, etc.

    Args: Same as Device.
    """

    config_section = 'BallDevices'
    collection = 'balldevices'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('BallDevice.' + name)
        super(BallDevice, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()

        # set our config defaults

        if 'ball_switches' not in self.config:
            self.config['ball_switches'] = None
        if 'exit_count_delay' not in self.config:
            self.config['exit_count_delay'] = ".5s"  # todo make optional
        if 'entrance_count_delay' not in self.config:
            self.config['entrance_count_delay'] = "0.5s"
        if 'eject_coil' not in self.config:
            self.config['eject_coil'] = None
        if 'eject_switch' not in self.config:
            self.config['eject_switch'] = None
        if 'entrance_switch' not in self.config:
            self.config['entrance_switch'] = None
        if 'jam_switch' not in self.config:
            self.config['jam_switch'] = None
        if 'eject_coil_hold_times' not in self.config:
            self.config['eject_coil_hold_times'] = list()
        if 'confirm_eject_type' not in self.config:
            self.config['confirm_eject_type'] = 'count'  # todo make optional?
        if 'confirm_eject_target' not in self.config:
            self.config['confirm_eject_target'] = None
        if 'balls_per_eject' not in self.config:
            self.config['balls_per_eject'] = 1
        if 'feeder_device' not in self.config:
            self.config['feeder_device'] = None
        if 'max_eject_attempts' not in self.config:
            self.config['max_eject_attempts'] = 0

        # figure out the ball capacity
        if 'ball_switches' in self.config:
            self.config['ball_switches'] = self.machine.string_to_list(
                self.config['ball_switches'])

        if 'ball_capacity' not in self.config:
            self.config['ball_capacity'] = len(self.config['ball_switches'])

        # initialize variables

        self.num_balls_contained = -999
        # Number of balls currently contained (held) in this device.
        # -999 indicates no count has taken place yet.

        # Set initial desired ball count.
        # Warning, do not change _num_balls_desired, rather use the
        # num_balls_desired (no leading underscore) setter
        if 'trough' in self.tags:
            self._num_balls_desired = self.config['ball_capacity']
        else:
            self._num_balls_desired = 0

        self.num_eject_attempts = 0
        # Counter of how many attempts to eject the current ball this device
        # has tried. Eventually it will give up.
        # todo make it eventually give up. :)
        # todo log attemps more than one?

        self.flag_ok_to_eject = False
        # Flag that indicates whether this device can eject a ball. (Based on
        # number of balls contained, whether there's a receiving device with
        # room, etc.

        self.flag_eject_in_progress = False

        self.flag_valid = False
        # Set once we pass the settling time of our switches. If a count comes
        # in while the valid flag is not set, we will get a count result of -999

        self.num_jam_sw_count = 0
        # How many times the jam switch has been activated since the last
        # successful eject.

        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize)

        self.num_balls_ejecting = 0
        # The number of balls that are currently in the process of being
        # ejected. This is either 0, 1, or whatever the num_balls_contained was
        # for devices that eject all their balls at once.

        self.flag_confirm_eject_via_count = False
        # Notifies the count_balls() method that it should confirm an eject if
        # it finds a ball missing. We need this to be a standalone variable
        # since sometimes other eject methods will have to "fall back" on count
        #-based confirmations.

        # Now configure the device
        self.configure()

    @property
    def num_balls_desired(self):
        return self._num_balls_desired

    @num_balls_desired.setter
    def num_balls_desired(self, balls):
        """Specifies how many balls this device desires to contain.

        Note that trough devices (ball devices tagged with 'trough') always
        desire to be full, so setting a new value here doesn't actually change
        a trough's desired ball count. That said, if a trough device receives
        a desired count value here that's lower than the current number of
        balls it contains, it will attempt to eject a ball (even though the
        desired count won't actually change.)
        """

        if 'trough' in self.tags:
            if balls < self.config['ball_capacity']:
                self.log.debug("About to call _eject() from trough due to "
                               "num_balls_desired count change which asked for "
                               "fewer balls than capacity")
                # troughs are special
                self._eject()
            return

        self.log.debug("Received request to change desired balls to %s", balls)

        # Make sure we set a valid desired value
        if balls <= self.config['ball_capacity']:
            self._num_balls_desired = balls
        else:
            self._num_balls_desired = self.config['ball_capacity']

        self.log.debug("Setting desired balls to %s", self._num_balls_desired)

        # Return if contained is -999. Pick it up on next count?
        if self.num_balls_contained == -999:
            return

        # What's our ball change?
        ball_change = self._num_balls_desired - self.num_balls_contained
        self.log.debug("Ball change to get to desired count: %s", ball_change)

        # Compare balls desired to balls contained to see if we have to act

        if ball_change > 0:  # We need more balls
            self.stage_ball()

        elif ball_change < 0:
            self.log.debug("num_balls_desired() found this device has too many "
                           "balls. About to call _eject()")
            self._eject()

    @property
    def num_balls_ejectable(self):
        balls = self.num_balls_contained

        if self.config['feeder_device']:
            balls += (self.machine.balldevices[self.config['feeder_device']].
                      num_balls_ejectable)

        return balls

    def configure(self, config=None):
        """Performs the actual configuration of the ball device based on the
        dictionary that was passed to it.

        Args:
            config: Python dictionary which holds the configuration settings.
        """

        # Merge in any new changes that were just passed
        if config:
            self.config.update(config)

        self.log.debug("Configuring device with: %s", self.config)

        # convert delay strings to ms ints
        if self.config['exit_count_delay']:
            self.config['exit_count_delay'] = \
                Timing.string_to_ms(self.config['exit_count_delay'])

        if self.config['entrance_count_delay']:
            self.config['entrance_count_delay'] = \
                Timing.string_to_ms(self.config['entrance_count_delay'])

        # Register for events
        self.machine.events.add_handler('balldevice_' + self.name +
                                        '_ball_eject_request',
                                        self._eject)

    def _initialize(self):
        # convert names to objects

        if self.config['ball_switches']:
            for i in range(len(self.config['ball_switches'])):
                self.config['ball_switches'][i] = (
                    self.machine.switches[self.config['ball_switches'][i]])

        if self.config['eject_coil']:
            self.config['eject_coil'] = (
                self.machine.coils[self.config['eject_coil']])

        if self.config['eject_switch']:
            self.config['eject_switch'] = (
                self.machine.switches[self.config['eject_switch']])

        if self.config['entrance_switch']:
            self.config['entrance_switch'] = (
                self.machine.switches[self.config['entrance_switch']])

        if self.config['jam_switch']:
            self.config['jam_switch'] = (
                self.machine.switches[self.config['jam_switch']])

        if self.config['confirm_eject_type'] == 'device' and (
                self.config['confirm_eject_target']):
            self.config['confirm_eject_target'] = (
                self.machine.balldevices[self.config['confirm_eject_target']])

        if self.config['confirm_eject_type'] == 'switch' and (
                self.config['confirm_eject_target']):
            self.config['confirm_eject_target'] = (
                self.machine.switches[self.config['confirm_eject_target']])

        if self.config['feeder_device']:
            self.config['feeder_device'] = (
                self.machine.balldevices[self.config['feeder_device']])

        # Register switch handlers with delays for entrance & exit counts
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                ms=self.config['entrance_count_delay'],
                callback=self.count_balls)
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=0,
                ms=self.config['exit_count_delay'],
                callback=self.count_balls)
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                ms=0,
                callback=self._invalidate)
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=0,
                ms=0,
                callback=self._invalidate)

        # Configure switch handlers for jam switch activity
        if self.config['jam_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['jam_switch'].name, state=1, ms=0,
                callback=self._jam_switch_handler)
            # todo do I also need to add inactive and make a smarter
            # handler?

        # Configure switch handlers for entrance switch activity
        if self.config['entrance_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['entrance_switch'].name, state=1, ms=0,
                callback=self._entrance_switch_handler)
            # todo do I also need to add inactive and make a smarter
            # handler?

        # if this device's target is another device, register for notification
        # of that device's successful eject so this device can set its ok to
        # eject flag and stage a ball if needed.

        if self.config['confirm_eject_type'] == 'device':
            self.machine.events.add_handler('balldevice_' +
                                        self.config['confirm_eject_target'].name
                                        + '_ball_eject_success',
                                        self.count_balls)

        # If this device has a feeder, register for notification of the feeder
        # becoming ok to eject.
        if self.config['feeder_device']:
            self.machine.events.add_handler('balldevice_' +
                                            self.config['feeder_device'].name
                                            + '_ok_to_eject',
                                            self.count_balls)

        # Get an initial ball count
        self.count_balls(stealth=True)

    def get_status(self, request=None):
        """Returns a dictionary of current status of this ball device.

        Args:
            request: A string of what status item you'd like to request.
                Default will return all status items.
                Options include:
                    * num_balls_contained
                    * flag_eject_in_progress
                    * num_balls_to_eject
                    * num_balls_desired

        Returns:
            A dictionary with the following keys:
                 * num_balls_contained
                * flag_eject_in_progress
                * num_balls_to_eject
                * num_balls_desired
        """
        if request == 'num_balls_contained':
            return self.num_balls_contained
        elif request == 'flag_eject_in_progress':
            return self.flag_eject_in_progress
        elif request == 'num_balls_to_eject':
            return self.num_balls_to_eject,
        elif request == 'num_balls_desired':
            return self.num_balls_desired
        else:
            return {'num_balls_contained': self.num_balls_contained,
                    'flag_eject_in_progress': self.flag_eject_in_progress,
                    'num_balls_to_eject': self.num_balls_to_eject,
                    'num_balls_desired': self.num_balls_desired
                    }

    def status_dump(self):
        """Dumps the full current status of the device to the log."""

        self.log.debug("+-----------------------------------------+")
        self.log.debug("| num_balls_contained: %s                  |",
                       self.num_balls_contained)
        self.log.debug("| flag_eject_in_progress: %s            |",
                       self.flag_eject_in_progress)
        self.log.debug("| flag_ok_to_eject: %s                  |",
                       self.flag_ok_to_eject)
        self.log.debug("| num_jam_sw_count: %s                     |",
                       self.num_jam_sw_count)
        self.log.debug("| num_balls_desired: %s                    |",
                       self.num_balls_desired)
        self.log.debug("| num_eject_attempts: %s                   |",
                       self.num_eject_attempts)
        self.log.debug("+-----------------------------------------+")

    def _invalidate(self):
        self.valid = False

    def count_balls(self, stealth=False, **kwargs):
        """Counts the balls in the device and processes any new balls that came
        in or balls that have gone out.

        Args:
            stealth: Boolean value that controls whether any events will be
                posted based on any ball count change info. If True, results
                will not be posted. If False, they will. Default is False.
        """
        self.log.debug("Counting balls")

        self.valid = True

        if self.num_balls_contained < 0 and self.num_balls_contained != -999:
            self.log.warning("Number of balls contained is negative (%s).",
                           self.num_balls_contained)
            # This should never happen

        if self.config['ball_switches']:

            ball_count = 0
            ball_change = 0
            previous_balls = self.num_balls_contained
            self.log.debug("Previous number of balls: %s", previous_balls)

            for switch in self.config['ball_switches']:
                valid = False
                if self.machine.switch_controller.is_active(switch.name,
                        ms=self.config['entrance_count_delay']):
                    ball_count += 1
                    valid = True
                    self.log.debug("Confirmed active switch: %s", switch.name)
                elif self.machine.switch_controller.is_inactive(switch.name,
                        ms=self.config['exit_count_delay']):
                    self.log.debug("Confirmed inactive switch: %s", switch.name)
                    valid = True

                if not valid:  # one of our switches wasn't valid long enough
                    # recount will happen automatically after the time passes
                    # via the switch handler for count
                    self.log.debug("Switch '%s' changed too recently. Aborting "
                                  "count & returning previous count value",
                                  switch.name)
                    self.valid = False
                    return previous_balls

            self.log.debug("Counted %s balls", ball_count)
            self.num_balls_contained = ball_count

            # Figure out if we gained or lost any balls since last count?
            if previous_balls == -999:  # This is the first time count
                # No "real" change since we didn't know previous value
                self.log.debug("Previous count was invalid. Don't know if we "
                              "gained or lost anything.")
                ball_change = 0
            else:
                ball_change = ball_count - previous_balls
                self.log.debug("Ball count change: %s", ball_change)

            # If we were waiting for a count-based eject confirmation, let's
            # confirm it now
            if (not ball_change and self.flag_confirm_eject_via_count and
                    self.flag_eject_in_progress):
                self._eject_success()
                # todo I think this is ok with `not ball_change`. If ball_change
                # is positive that means the ball fell back in or a new one came
                # in. We can't tell the difference, but hey, we're using count-
                # based eject confirmation which sucks anyway, so them's the
                # ropes. If ball_change is negative then I don't know what the
                # heck happened.

            self.set_ok_to_eject()
            self.status_dump()

            if ball_change > 0:
                self._balls_added(ball_change)
            elif ball_change < 0:
                    self._balls_missing(ball_change)

        else:  # this device doesn't have any ball switches
            self.log.debug("Received request to count balls, but we don't have"
                           " any ball switches. So we're just returning the"
                           " old count.")
            if self.num_balls_contained == -999:
                self.num_balls_contained = 0
            # todo add support for virtual balls

        if self.num_balls_contained > self.num_balls_desired:
            self.log.debug("Count_balls() fround more balls than desired. "
                           "About to call _eject()")
            self._eject()

        return self.num_balls_contained

    def _balls_added(self, balls):
        # Called when ball_count finds new balls in this device
        if self.flag_eject_in_progress:
            self._eject_failed()
            if 'drain' in self.tags:
                self.log.debug("About to call _eject() because we got a new ball"
                               "in a drain device while the EIP flag was set.")
                self._eject()  # drains are special
                # todo I think we need to change this. What happens if a ball
                # drains before we get the eject confirmation? We'll try to
                # eject another. Wonder if we should change our target to not
                # ok to receive? Meh, that won't work because if we truly
                # have an eject failure then it won't restart. We need to set a
                # delay to reset the target device if it doesn't receive a ball.

        else:
        # No ejects in progress, so we assume this is a valid new ball?
            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_enter', balls=balls)
            for tag in self.tags:
                self.machine.events.post('sw_' + tag)
                # todo I don't like this. Change big shot and remove
                # or maybe pass tags along with the event post?

    def _balls_missing(self, balls):
        # Called when ball_count finds that balls are missing from this device

        self.log.warning("%s ball(s) missing from device", abs(balls))

        # todo dunno if there's any action we should take here? This should
        # never happen unless someone takes the glass off and steals a ball or
        # unless there's a ball switch or a ball randomly falls out of a device?

    def is_full(self):
        """Checks to see if this device is full, meaning it is holding either
        the max number of balls it can hold, or it's holding all the known balls
        in the machine.

        Returns: True or False

        """
        if self.num_balls_contained == self.ball_capacity:
            return True
        elif self.num_balls_contained == \
                self.machine.ball_controller.num_balls_known:
            return True
        else:
            return False

    def _jam_switch_handler(self):
        # The device's jam switch was just activated.
        # This method is typically used with trough devices to figure out if
        # balls fell back in.

        self.num_jam_sw_count += 1
        self.log.debug("Ball device %s jam switch hit. New count: %s",
                       self.name, self.num_jam_sw_count)

    def set_ok_to_eject(self):
        """Checks whether it's ok for this device to eject and sets the flag.

        Returns: True (device is ok to eject) or False.
        """
        initial_value = self.flag_ok_to_eject

        self.flag_ok_to_eject = True

        # Now let's look for a reason for this not to be true

        if self.config['eject_switch']:  # do we have an eject switch?
            if self.machine.switch_controller.is_inactive(
                    self.config['eject_switch'].name):  # is it inactive?
                self.flag_ok_to_eject = False
        elif not self.num_balls_contained:  # If not, do we have a ball?
            self.flag_ok_to_eject = False

        # Are we ejecting into a device, and if so, does it have capacity?
        if self.config['confirm_eject_type'] == 'device':
            if not self.config['confirm_eject_target'].is_ok_to_receive():
                self.flag_ok_to_eject = False

        if self.flag_ok_to_eject:

            if not initial_value:
                # We were not ok and now we are, so let's post an event of that
                self.machine.events.post('balldevice_' + self.name +
                                         '_ok_to_eject')

            return True

        else:
            return False

    def is_ok_to_receive(self):
        """Checks whether it's ok for this device to receive any balls.

        Returns: An integer value of the number of balls this device can
            receive. A return value of 0 means that this device is full and/or
            that it's not able to receive any balls at this time.
        """

        if self.config['ball_capacity'] - self.num_balls_contained < 0:
            self.log.warning("Device reporting more balls contained than its "
                           "capacity.")

        return self.config['ball_capacity'] - self.num_balls_contained

    def stage_ball(self):
        """Used to make sure the device has a ball 'staged' and ready to
        eject.
        """
        self.log.debug("In stage_ball. EIP: %s", self.flag_eject_in_progress)

        if self.flag_eject_in_progress:
            self.log.debug("Received request to stage ball, but we can't since "
                          "there's an eject in progress.")
            return

        self.log.debug("Staging Ball")
        if not self.flag_ok_to_eject:
            self.log.debug("No ball ready to eject")
            if self.config['feeder_device']:
                # get a ball from the feeder device
                # if feeder is trying to eject, then do nothing.
                if self.config['feeder_device'].flag_ok_to_eject:
                    self.log.debug("Requesting ball from feeder device: '%s'",
                                   self.config['feeder_device'].name)
                    self.config['feeder_device'].num_balls_desired -=1
                    return True
                else:
                    self.log.debug("Feeder device '%s' is not ok to eject "
                                   "already or is in the process of ejecting, "
                                   "so we're doing nothing.",
                                   self.config['feeder_device'].name)
                    return False
            else:
                self.log.warning("No feeder device! Stage failed!")
                return False
        else:
            self.log.debug("Ball is already staged and ready to go")
            return True

    def _eject_event_handler(self):
        # We received the event that should eject this ball.

        self.num_balls_desired -= 1

        if not self.flag_ok_to_eject:
            self.stage_ball()

    def stop(self):
        """Stops all activity in a device.

        Cancels all pending eject requests. Cancels eject confirmation checks.
        """
        self.log.debug("Stopping all activity via stop()")
        self.flag_eject_in_progress = False
        self.num_balls_to_eject = 0
        self.num_jam_sw_count = 0

        self._cancel_eject_confirmation()
        self.count_balls()  # need this since we're canceling the eject conf

    def _eject(self):
        # Performs the actual eject attempts and sets up eject confirmations

        self.log.debug("Entering _eject()")

        if not self.config['eject_coil']:
            self.log.debug("This device has no eject coil, there's nothing to do"
                          " here. We assume this is a manual plunger and wait "
                          "for the player to eject the ball.")
            return

        if (self.num_balls_contained <= self.num_balls_desired and
                'trough' not in self.tags):
            self.log.debug("Fewer balls contained than desired. Aborting eject")
            return False

        if self.flag_eject_in_progress:
            self.log.debug("Eject flag in progress. Aborting eject")
            return False  # Don't want to get in the way of a current eject

        if not self.flag_ok_to_eject:  # todo do we still need this?
            self.stage_ball()
                # Todo how do we automatically get a ball from a feeder device?
                # for add_ball_live, if we don't have a ball then get one from
                # the feeder
            self.log.debug("Ok to eject flag not set. Aborting eject")
            return

        else:
            self.log.debug("Proceeding with the eject")
            self.flag_eject_in_progress = True
            self.num_eject_attempts += 1

            if self.config['jam_switch']:
                self.num_jam_sw_count = 0
                if self.machine.switch_controller.is_active(
                        self.config['jam_switch'].name):
                    self.num_jam_sw_count += 1
                    # catches if the ball is blocking the switch to
                    # begin with, todo we have to get smart here

            self._setup_eject_confirmation()

            if self.config['balls_per_eject'] == 1:
                self.num_balls_contained -= 1
                self.num_balls_ejecting = 1
            else:
                self.num_balls_ejecting = self.num_balls_contained
                self.num_balls_contained = 0

            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_attempt',
                                     balls=self.num_balls_ejecting)
            # todo if the event queue is busy, this event will be
            # queued, yet the coil pulse happens now. Is that ok?

            self.config['eject_coil'].pulse()
            # todo add support for hold coils with var. release times

    def _setup_eject_confirmation(self, style=None):
        # Called after an eject request to confirm the eject. The exact method
        # of confirmation depends on how this ball device has been configured.
        self.log.debug("Setting up eject confirmation.")

        self.flag_confirm_eject_via_count = False

        if self.config['confirm_eject_type'] == 'device':
            self.log.debug("Will confirm eject via ball entry into '%s'",
                          self.config['confirm_eject_target'].name)
            # watch for ball entry event on that device
            # Note this must be higher priority than the failed eject handler
            self.machine.events.add_handler(
                'balldevice_' + self.config['confirm_eject_target'].name +
                '_ball_enter', self._eject_success, 2)

        elif self.config['confirm_eject_type'] == 'switch':
            self.log.debug("Will confirm eject via activation of switch '%s'",
                           self.config['confirm_eject_target'].name)
            # watch for that switch to activate momentarily
            # todo add support for a timed switch here
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['confirm_eject_target'].name,
                callback=self._eject_success,
                state=1, ms=0)

        elif self.config['confirm_eject_type'] == 'event':
            self.log.debug("Will confirm eject via posting of event '%s'",
                          self.config['confirm_eject_target'].name)
            # watch for that event
            self.machine.events.add_handler(
                self.config['confirm_eject_target'].name, self._eject_success)

        elif self.config['confirm_eject_type'] == 'playfield':
            # This option is only used with 'playfield' when no balls are live

            if not self.machine.ball_controller.num_balls_live:
                self.log.debug("Will confirm eject when a playfield switch is hit")
                self.machine.events.add_handler('sw_ballLive',
                                                self._eject_success)
            else:
                self.log.debug("Will confirm eject via recount of ball switches.")
                self.flag_confirm_eject_via_count = True

        elif self.config['confirm_eject_type'] == 'count':
            # todo I think we need to set a delay to recount? Because if the
            # ball re-enters in less time than the exit delay, then the switch
            # handler won't have time to reregister it.
            self.log.debug("Will confirm eject via recount of ball switches.")
            self.flag_confirm_eject_via_count = True

        else:
            # If there's no confirm eject type specified, then we'll just
            # confirm it right away.
            self.log.debug("No eject confirmation configured. Confirming now.")
            self._eject_success()
            return

    def _cancel_eject_confirmation(self):
        self.log.debug("Canceling eject confirmations")
        self.flag_eject_in_progress = False
        # Remove any event watching for success
        self.machine.events.remove_handler(self._eject_success)

        # Remove any switch handlers
        if self.config['confirm_eject_type'] == 'switch':
            self.machine.switch_controller.remove_switch_handler(
                switch_name=self.config['confirm_eject_target'].name,
                callback=self._eject_success,
                state=1, ms=0)

    def _eject_success(self, **kwargs):
        # We got an eject success for this device.
        # **kwargs because there are many ways to get here, some with kwargs and
        # some without. Also, since there are many ways we can get here, let's
        # first make sure we actually had an eject in progress
        self.log.debug("In _eject_success. EIP: %s", self.flag_eject_in_progress)
        self.flag_confirm_eject_via_count = False
        if self.flag_eject_in_progress:
            self.log.debug("Confirmed successful eject")

            self.num_jam_sw_count = 0
            self.num_eject_attempts = 0
            self.flag_eject_in_progress = False
            balls_ejected = self.num_balls_ejecting
            self.num_balls_ejecting = 0
            self.set_ok_to_eject()

            # todo cancel post eject check delay

            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_success',
                                     balls=balls_ejected)

        else:
            self.log.warning("We got to '_eject_success' but no eject was in "
                             "progress. Just FYI that something's weird.")
            # this should never happen

        self._cancel_eject_confirmation()

        self.count_balls()  # picks up any remaining balls we should eject

    def _eject_failed(self, balls=0):

        self.log.debug("Eject Failed")
        self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_failed')

        # todo audit the number of failed ejects for this device

        self._cancel_eject_confirmation()

        # do we do anything here? Switch handlers should pick this up

        # todo increase our attempt count? meh, switch handler can do that too.


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
