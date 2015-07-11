""" Contains the base class for ball devices."""
# ball_device.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
from collections import deque
import time

from mpf.system.tasks import DelayManager
from mpf.system.devices import Device
from mpf.system.timing import Timing
from mpf.system.config import Config


class BallDevice(Device):
    """Base class for a 'Ball Device' in a pinball machine.

    A ball device is anything that can hold one or more balls, such as a
    trough, an eject hole, a VUK, a catapult, etc.

    Args: Same as Device.
    """

    config_section = 'balldevices'
    collection = 'balldevices'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('BallDevice.' + name)
        super(BallDevice, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()

        # set config defaults
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
        if 'captures_from' not in self.config:
            self.config['captures_from'] = 'playfield'
        if 'eject_targets' not in self.config:
            self.config['eject_targets'] = ['playfield']
        else:
            self.config['eject_targets'] = Config.string_to_list(
                self.config['eject_targets'])

        if 'eject_timeouts' not in self.config:
            self.config['eject_timeouts'] = list()
        else:
            self.config['eject_timeouts'] = Config.string_to_list(
                self.config['eject_timeouts'])

        if 'confirm_eject_switch' not in self.config:
            self.config['confirm_eject_switch'] = None
        if 'confirm_eject_event' not in self.config:
            self.config['confirm_eject_event'] = None
        if 'balls_per_eject' not in self.config:
            self.config['balls_per_eject'] = 1
        if 'max_eject_attempts' not in self.config:
            self.config['max_eject_attempts'] = 0

        if 'ball_switches' in self.config:
            self.config['ball_switches'] = Config.string_to_list(
                self.config['ball_switches'])
        else:
            self.config['ball_switches'] = []

        if 'ball_capacity' not in self.config:
            self.config['ball_capacity'] = len(self.config['ball_switches'])

        if 'debug' not in self.config:
            self.config['debug'] = False

        # initialize variables

        self.balls = 0
        # Number of balls currently contained (held) in this device..

        self.eject_queue = deque()
        # Queue of the list of eject targets (ball devices) for the balls this
        # device is trying to eject.

        self.num_eject_attempts = 0
        # Counter of how many attempts to eject the current ball this device
        # has tried. Eventually it will give up.
        # todo log attemps more than one?

        self.eject_in_progress_target = None
        # The ball device this device is currently trying to eject to

        self.num_balls_requested = 0
        # The number of balls this device is in the process of trying to get.

        self.num_jam_switch_count = 0
        # How many times the jam switch has been activated since the last
        # successful eject.

        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize)

        self.num_balls_ejecting = 0
        # The number of balls that are currently in the process of being
        # ejected. This is either 0, 1, or whatever the balls was
        # for devices that eject all their balls at once.

        self.flag_confirm_eject_via_count = False
        # Notifies the count_balls() method that it should confirm an eject if
        # it finds a ball missing. We need this to be a standalone variable
        # since sometimes other eject methods will have to "fall back" on count
        #-based confirmations.

        self.valid = False
        self.need_first_time_count = True
        self._playfield = False

        # Now configure the device
        self.configure()

    @property
    def num_balls_ejectable(self):
        return self.balls

        # todo look at upstream devices

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

        # Look for eject requests for this device
        self.machine.events.add_handler('balldevice_' + self.name +
                                        '_ball_eject_request',
                                        self.eject)
        # todo change event name to action_balldevice_name_eject_request

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

        if self.config['confirm_eject_type'] == 'switch' and (
                self.config['confirm_eject_target']):
            self.config['confirm_eject_switch'] = (
                self.machine.switches[self.config['confirm_eject_switch']])

        if self.config['eject_targets']:
            for i in range(len(self.config['eject_targets'])):
                self.config['eject_targets'][i] = (
                    self.machine.balldevices[self.config['eject_targets'][i]])

        # make sure the eject timeouts list matches the length of the eject targets
        if (len(self.config['eject_timeouts']) <
                len(self.config['eject_targets'])):
            self.config['eject_timeouts'] += [None] * (
                len(self.config['eject_targets']) -
                len(self.config['eject_timeouts']))

        timeouts_list = self.config['eject_timeouts']
        self.config['eject_timeouts'] = dict()

        for i in range(len(self.config['eject_targets'])):
            self.config['eject_timeouts'][self.config['eject_targets'][i]] = (
                Timing.string_to_ms(timeouts_list[i]))
        # End code to create timeouts list -------------------------------------

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
            # todo do we also need to add inactive and make a smarter
            # handler?

        # Configure switch handlers for entrance switch activity
        if self.config['entrance_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['entrance_switch'].name, state=1, ms=0,
                callback=self._entrance_switch_handler)
            # todo do we also need to add inactive and make a smarter
            # handler?

        # Configure event handlers to watch for target device status changes
        for target in self.config['eject_targets']:
            # Target device is requesting a ball
            self.machine.events.add_handler('balldevice_' +
                                            target.name
                                            + '_ball_request',
                                            self.eject,
                                            target=target,
                                            get_ball=True)

            # Target device is now able to receive a ball
            self.machine.events.add_handler('balldevice_' +
                                            target.name
                                            + '_ok_to_receive',
                                            self._do_eject)

        # Get an initial ball count
        self.count_balls(stealth=True)

    def get_status(self, request=None):
        """Returns a dictionary of current status of this ball device.

        Args:
            request: A string of what status item you'd like to request.
                Default will return all status items.
                Options include:
                * balls
                * eject_in_progress_target
                * eject_queue

        Returns:
            A dictionary with the following keys:
                * balls
                * eject_in_progress_target
                * eject_queue
        """
        if request == 'balls':
            return self.balls
        elif request == 'eject_in_progress_target':
            return self.eject_in_progress_target
        elif request == 'eject_queue':
            return self.eject_queue,
        else:
            return {'balls': self.balls,
                    'eject_in_progress_target': self.eject_in_progress_target,
                    'eject_queue': self.eject_queue,
                    }

    def status_dump(self):
        """Dumps the full current status of the device to the log."""

        if self.eject_in_progress_target:
            eject_name = self.eject_in_progress_target.name
        else:
            eject_name = 'None'

        self.log.debug("+-----------------------------------------+")
        self.log.debug("| balls: %s                  |",
                       self.balls)
        self.log.debug("| eject_in_progress_target: %s",
                       eject_name)
        self.log.debug("| num_balls_ejecting: %s                   |",
                       self.num_balls_ejecting)
        self.log.debug("| num_jam_switch_count: %s                     |",
                       self.num_jam_switch_count)
        self.log.debug("| num_eject_attempts: %s                   |",
                       self.num_eject_attempts)
        self.log.debug("| num_balls_requested: %s                  |",
                       self.num_balls_requested)
        self.log.debug("| eject queue: %s",
                       self.eject_queue)
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
            **kwargs: Catches unexpected args since this method is used as an
                event handler.
        """
        self.log.debug("Counting balls")

        self.valid = True

        if self.config['ball_switches']:

            ball_count = 0
            ball_change = 0
            previous_balls = self.balls
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
            self.balls = ball_count

            # Figure out if we gained or lost any balls since last count?
            if self.need_first_time_count:
                self.log.debug("This is a first time count. Don't know if we "
                              "gained or lost anything.")
                # No "real" change since we didn't know previous value
                ball_change = 0
            else:
                ball_change = ball_count - previous_balls
                self.log.debug("Ball count change: %s", ball_change)

            # If we were waiting for a count-based eject confirmation, let's
            # confirm it now
            if (not ball_change and self.flag_confirm_eject_via_count and
                    self.eject_in_progress_target):
                self._eject_success()
                # todo I think this is ok with `not ball_change`. If ball_change
                # is positive that means the ball fell back in or a new one came
                # in. We can't tell the difference, but hey, we're using count-
                # based eject confirmation which sucks anyway, so them's the
                # ropes. If ball_change is negative then I don't know what the
                # heck happened.

            self.status_dump()

            if ball_change > 0:
                self._balls_added(ball_change)
            elif ball_change < 0:
                    self._balls_missing(ball_change)

        else:  # this device doesn't have any ball switches
            self.log.debug("Received request to count balls, but we don't have"
                           " any ball switches. So we're just returning the"
                           " old count.")
            if self.need_first_time_count:
                self.balls = 0
            # todo add support for virtual balls

        self.need_first_time_count = False

        if self.balls < 0:
            self.balls = 0
            self.log.warning("Number of balls contained is negative (%s).",
                             self.balls)
            # This should never happen

        return self.balls

    def _balls_added(self, balls):
        # Called when ball_count finds new balls in this device

        # If this device received a new ball while a current eject was in
        # progress, let's try to figure out whether an actual new ball entered
        # or whether the current ball it was trying to eject fell back in.
        # Note we can only do this for devices that have a jam switch.

        if (self.eject_in_progress_target and self.config['jam_switch'] and
                self.num_jam_switch_count > 1):
            # If the jam switch count is more than 1, we assume the ball it was
            # trying to eject fell back in.
            self.log.debug("Jam switch count: %s. Assuming eject failed.",
                           self.num_jam_switch_count)
            self.eject_failed()
            return

        elif ((self.eject_in_progress_target and self.config['jam_switch'] and
                self.num_jam_switch_count == 1) or
                not self.eject_in_progress_target):
            # If there's an eject in progress with a jam switch count of only 1,
            # or no eject in progress, we assume this was a valid new ball.

            # If this device is not expecting any balls, we assuming this one
            # came from the playfield. Post this event so the playfield can keep
            # track of how many balls are out.
            if not self.num_balls_requested:
                self.machine.events.post('balldevice_captured_from_' +
                                         self.config['captures_from'],
                                         balls=balls)

            # Post the relay event as other handlers might be looking for to act
            # on the ball entering this device.
            self.machine.events.post_relay('balldevice_' + self.name +
                                           '_ball_enter',
                                            balls=balls,
                                            callback=self._balls_added_callback)

    def _balls_added_callback(self, balls, **kwargs):
        # Callback event for the balldevice_<name>_ball_enter relay event

        # If we still have balls here, that means that no one claimed them, so
        # essentially they're "stuck." So we just eject them... unless this
        # device is tagged 'trough' in which case we let it keep them.
        if balls and 'trough' not in self.tags:
            self.eject(balls)

        self.log.debug("In the balls added callback")
        self.log.debug("Eject queue: %s", self.eject_queue)

        #todo we should call the ball controller in case it wants to eject a
        # ball from a different device?

        if self.eject_queue:
            self.log.debug("A ball was added and we have an eject_queue, so "
                           "we're going to process that eject now.")
            self._do_eject()

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
        if self.balls == self.config['ball_capacity']:
            return True
        elif self.balls == self.machine.ball_controller.num_balls_known:
            return True
        else:
            return False

    def _jam_switch_handler(self):
        # The device's jam switch was just activated.
        # This method is typically used with trough devices to figure out if
        # balls fell back in.

        self.num_jam_switch_count += 1
        self.log.debug("Ball device %s jam switch hit. New count: %s",
                       self.name, self.num_jam_switch_count)

    def _entrance_switch_handler(self):
        # A ball has triggered this device's entrance switch

        if not self.config['ball_switches']:
            self.balls += 1
            self._balls_added(1)

    def get_additional_ball_capacity(self):
        """Returns an integer value of the number of balls this device can
            receive. A return value of 0 means that this device is full and/or
            that it's not able to receive any balls at this time due to a
            current eject_in_progress.
        """

        if self.num_balls_ejecting:
            # This device is in the process of ejecting a ball, so it shouldn't
            # receive any now.

            return 0

        if self.config['ball_capacity'] - self.balls < 0:
            self.log.warning("Device reporting more balls contained than its "
                             "capacity.")

        return self.config['ball_capacity'] - self.balls

    def request_ball(self, balls=1):
        """Request that one or more balls is added to this device.

        Args:
            balls: Integer of the number of balls that should be added to this
                device. A value of -1 will cause this device to try to fill
                itself.

        Note that a device will never request more balls than it can hold. Also,
        only devices that are fed by other ball devices (or a combination of
        ball devices and diverters) can make this request. e.g. if this device
        is fed from the playfield, then this request won't work.
        """

        self.log.debug("In request_ball. balls: %s", balls)

        if self.eject_in_progress_target:
            self.log.debug("Received request to request a ball, but we can't "
                           "since there's an eject in progress.")
            return False

        if not self.get_additional_ball_capacity():
            self.log.debug("Received request to request a ball, but we can't "
                           "since it's not ok to receive.")
            return False

        # How many balls are we requesting?
        remaining_capacity = (self.config['ball_capacity'] -
                              self.balls -
                              self.num_balls_requested)

        if remaining_capacity < 0:
            remaining_capacity = 0

        # Figure out how many balls we can request
        if balls == -1 or balls > remaining_capacity:
            balls = remaining_capacity

        if not balls:
            return 0

        self.num_balls_requested += balls

        self.log.debug("Requesting Ball(s). Balls=%s", balls)

        # set event handler to watch for receiving a ball
        self.machine.events.add_handler('balldevice_' + self.name +
                                        '_ball_enter',
                                        self._requested_ball_received)

        self.machine.events.post('balldevice_' + self.name + '_ball_request',
                                 balls=balls)

        return balls

    def _requested_ball_received(self, balls):
        # Responds to its own balldevice_<name>_ball_enter relay event
        # We do this since we need something to act on the balls being received,
        # otherwise it would think they were unexpected and eject them.

        # Figure out how many of the new balls were requested
        unexpected_balls = balls - self.num_balls_requested
        if unexpected_balls < 0:
            unexpected_balls = 0

        # Figure out how many outstanding ball requests we have
        self.num_balls_requested -= balls

        if self.num_balls_requested <= 0:
            self.num_balls_requested = 0
            self.machine.events.remove_handler(self._requested_ball_received)

        return {'balls': unexpected_balls}

    def _cancel_request_ball(self):
        self.machine.events.post('balldevice_' + self.name +
                                 '_cancel_ball_request')

    def _eject_event_handler(self):
        # We received the event that should eject this ball.

        if not self.balls:
            self.request_ball()

    def stop(self):
        """Stops all activity in this device.

        Cancels all pending eject requests. Cancels eject confirmation checks.
        """
        self.log.debug("Stopping all activity via stop()")
        self.eject_in_progress_target = None
        self.eject_queue = deque()
        self.num_jam_switch_count = 0

        # todo jan19 anything to add here?

        self._cancel_eject_confirmation()
        self.count_balls()  # need this since we're canceling the eject conf

    def eject(self, balls=1, target=None, timeout=None, get_ball=False):
        """Ejects one or more balls from the device.

        Args:
            balls: Integer of the number of balls to eject. Default is 1.
            target: Optional target that should receive the ejected ball(s),
                either a string name of the ball device or a ball device
                object. Default is None which means this device will eject this
                ball to the first entry in the eject_targets list.
            timeout: How long (in ms) to wait for the ball to make it into the
                target device after the ball is ejected. A value of ``None``
                means the default timeout from the config file will be used. A
                value of 0 means there is no timeout.
            get_ball: Boolean as to whether this device should attempt to get
                a ball to eject if it doesn't have one. Default is False.

        Note that if this device's 'balls_per_eject' configuration is more than
        1, then it will eject the nearest number of balls it can.
        """

        # Figure out the eject target

        if balls < 1:
            self.log.warning("Received request to eject %s balls, which doesn't"
                             " make sense. Ignoring...")
            return False

        if not target:
            target = self.config['eject_targets'][0]

        elif type(target) is str:
            target = self.machine.balldevices[target]

        self.log.debug("Received request to eject %s ball(s) to target '%s'",
                       balls, target.name)

        if not self.config['eject_coil']:
            self.log.debug("This device has no eject coil, so we're assuming "
                           "a manual eject by the player.")
            timeout = 0  # unlimited since who knows how long the player waits

        # Set the timeout for this eject
        if timeout is None:
            timeout = self.config['eject_timeouts'][target]

        # Set the number of balls to eject

        balls_to_eject = balls

        if balls_to_eject > self.balls and not get_ball:
            balls_to_eject = self.balls

        # Add one entry to the eject queue for each ball that's ejecting
        self.log.debug('Adding %s ball(s) to the eject_queue.', balls_to_eject)
        for i in range(balls_to_eject):
            self.eject_queue.append((target, timeout))

        self._do_eject()

    def eject_all(self, target=None):
        """Ejects all the balls from this device

        Args:
            target: The string or BallDevice target for this eject. Default of
                None means `playfield`.

        Returns:
            True if there are balls to eject. False if this device is empty.
        """
        self.log.debug("Ejecting all balls")
        if self.balls > 0:
            self.eject(balls=self.balls, target=target)
            return True
        else:
            return False

    def _do_eject(self, **kwargs):
        # Performs the actual eject attempts and sets up eject confirmations
        # **kwargs just because this method is registered for various events
        # which might pass them.

        self.log.debug("Entering _do_eject(). Current in progress target: %s. "
                       "Eject queue: %s",
                       self.eject_in_progress_target, self.eject_queue)

        if self.eject_in_progress_target:
            self.log.debug("Current eject in progress with target: %s. Aborting"
                           " eject.", self.eject_in_progress_target)
            return False  # Don't want to get in the way of a current eject

        if not self.balls and not self.num_balls_requested:
            self.log.debug("Don't have any balls. Requesting one.")
            self.request_ball()
            # Once the ball is delivered then the presence of the eject_queue
            # will re-start this _do_eject() process
            return False

        elif self.eject_queue and self.balls:
            self.log.debug("We have an eject queue: %s", self.eject_queue)

            target = self.eject_queue[0][0]  # first item, first part of tuple

            if not target.get_additional_ball_capacity():
                self.log.debug("Target device '%s' is not able to receive now. "
                               "Aborting eject. Will retry when target can "
                               "receive.", target.name)
                return False

            else:
                self.log.debug("Proceeding with the eject")

                self.log.debug("Setting eject_in_progress_target, timeout")
                self.eject_in_progress_target, timeout = (
                    self.eject_queue.popleft())

                self.num_eject_attempts += 1

                if self.config['jam_switch']:
                    self.num_jam_switch_count = 0
                    if self.machine.switch_controller.is_active(
                            self.config['jam_switch'].name):
                        self.num_jam_switch_count += 1
                        # catches if the ball is blocking the switch to
                        # begin with, todo we have to get smart here

                if self.config['balls_per_eject'] == 1:
                    self.num_balls_ejecting = 1
                else:
                    self.num_balls_ejecting = self.balls

                self.machine.events.post('balldevice_' + self.name +
                                         '_ball_eject_attempt',
                                         balls=self.num_balls_ejecting,
                                         target=self.eject_in_progress_target,
                                         timeout=timeout,
                                         callback=self._fire_eject_coil)
                # Fire the coil via a callback in case there are events in the
                # queue. This ensures that the coil pulse happens when this
                # event is posted instead of firing right away.

    def _eject_status(self):
        if self.config['debug']:

            self.log.info("DEBUG: Eject duration: %ss. Target: %s",
                          round(time.time() - self.eject_start_time, 2),
                          self.eject_in_progress_target.name)

    def _fire_eject_coil(self, target, timeout=None, **kwargs):

        self._setup_eject_confirmation(self.eject_in_progress_target, timeout)

        self.balls -= self.num_balls_ejecting

        try:
            self.config['eject_coil'].pulse()
            # todo add support for hold coils with variable release times
            self.log.debug("Firing eject coil. num_balls_ejecting: %s. New "
                           "balls: %s.",
                           self.num_balls_ejecting, self.balls)
        except AttributeError:
            self.log.debug("Waiting for player to manually eject ball(s)")

    def _setup_eject_confirmation(self, target=None, timeout=0):
        # Called after an eject request to confirm the eject. The exact method
        # of confirmation depends on how this ball device has been configured
        # and what target it's ejecting to

        # args are target device and timeout in ms

        self.log.debug("Setting up eject confirmation.")

        if self.config['debug']:
            self.eject_start_time = time.time()
            self.log.info("DEBUG: Eject start time: %s", self.eject_start_time)
            self.machine.events.add_handler('timer_tick', self._eject_status)

        self.flag_confirm_eject_via_count = False

        if self.config['confirm_eject_type'] == 'target':

            if not target:
                self.log.error("we got an eject confirmation request with no "
                               "target. This shouldn't happen. Post to the "
                               "forum if you see this.")
                raise Exception("we got an eject confirmation request with no "
                               "target. This shouldn't happen. Post to the "
                               "forum if you see this.")

            if timeout:
                # set up the delay to check for the failed the eject
                self.delay.add(name='target_eject_confirmation_timeout',
                               ms=timeout,
                               callback=self.eject_failed)

            self.log.debug("Will confirm eject via ball entry into '%s' with a "
                           "confirmation timeout of %sms", target.name, timeout)

            # watch for ball entry event on the target device
            # Note this must be higher priority than the failed eject handler
            self.machine.events.add_handler(
                'balldevice_' + target.name +
                '_ball_enter', self._eject_success, priority=1000)

        elif self.config['confirm_eject_type'] == 'switch':
            self.log.debug("Will confirm eject via activation of switch '%s'",
                           self.config['confirm_eject_switch'].name)
            # watch for that switch to activate momentarily
            # todo add support for a timed switch here
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['confirm_eject_switch'].name,
                callback=self._eject_success,
                state=1, ms=0)

        elif self.config['confirm_eject_type'] == 'event':
            self.log.debug("Will confirm eject via posting of event '%s'",
                           self.config['confirm_eject_event'])
            # watch for that event
            self.machine.events.add_handler(
                self.config['confirm_eject_event'], self._eject_success)

        elif self.config['confirm_eject_type'] == 'count':
            # todo I think we need to set a delay to recount? Because if the
            # ball re-enters in less time than the exit delay, then the switch
            # handler won't have time to reregister it.
            self.log.debug("Will confirm eject via recount of ball switches.")
            self.flag_confirm_eject_via_count = True

        elif (self.config['confirm_eject_type'] == 'playfield' and
                target.is_playfield()):

            if target.ok_to_confirm_ball_via_playfield_switch():
                self.log.debug("Will confirm eject when a %s switch is "
                               "hit", target.name)
                self.machine.events.add_handler('sw_' + target.name + '_active',
                                                self._eject_success)
            else:
                self.log.debug("Will confirm eject via recount of ball "
                               "switches.")
                self.flag_confirm_eject_via_count = True

        else:
            # If there's no confirm eject type specified, then we'll just
            # confirm it right away.
            self.log.debug("No eject confirmation configured. Confirming now.")
            self._eject_success()
            return

    def _cancel_eject_confirmation(self):
        self.log.debug("Canceling eject confirmations")
        self.eject_in_progress_target = None
        self.num_eject_attempts = 0

        # Remove any event watching for success
        self.machine.events.remove_handler(self._eject_success)

        # Remove any switch handlers
        if self.config['confirm_eject_type'] == 'switch':
            self.machine.switch_controller.remove_switch_handler(
                switch_name=self.config['confirm_eject_switch'].name,
                callback=self._eject_success,
                state=1, ms=0)

        # Remove any delays that were watching for failures
        self.delay.remove('target_eject_confirmation_timeout')

    def _eject_success(self, **kwargs):
        # We got an eject success for this device.
        # **kwargs because there are many ways to get here, some with kwargs and
        # some without. Also, since there are many ways we can get here, let's
        # first make sure we actually had an eject in progress

        self.log.debug("In _eject_success. Eject target: %s",
                       self.eject_in_progress_target)

        if self.config['debug']:
            self.log.info("DEBUG: Eject duration: %ss",
                          time.time() - self.eject_start_time)
            self.machine.events.remove_handler(self._eject_status)

        # Reset flags for next time
        self.flag_confirm_eject_via_count = False
        self.flag_pending_playfield_confirmation = False

        if self.eject_in_progress_target:
            self.log.debug("Confirmed successful eject")

            # Creat a temp attribute here so the real one is None when the
            # event is posted.
            eject_target = self.eject_in_progress_target
            self.num_jam_switch_count = 0
            self.num_eject_attempts = 0
            self.eject_in_progress_target = None
            balls_ejected = self.num_balls_ejecting
            self.num_balls_ejecting = 0

            # todo cancel post eject check delay

            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_success',
                                     balls=balls_ejected,
                                     target=eject_target)

        else:  # this should never happen
            self.log.warning("We got to '_eject_success()' but no eject was in "
                             "progress. Just FYI that something's weird.")

        self._cancel_eject_confirmation()

        if self.eject_queue:
            self._do_eject()

    def eject_failed(self, retry=True, force_retry=False):
        """Marks the current eject in progress as 'failed.'

        Note this is not typically a method that would be called manually. It's
        called automatically based on ejects timing out or balls falling back
        into devices while they're in the process of ejecting. But you can call
        it manually if you want to if you have some other way of knowing that
        the eject failed that the system can't figure out on it's own.

        Args:
            retry: Boolean as to whether this eject should be retried. If True,
                the ball device will retry the eject again as long as the
                'max_eject_attempts' has not been exceeded. Default is True.
            force_retry: Boolean that forces a retry even if the
                'max_eject_attempts' has been exceeded. Default is False.

        """

        self.log.debug("Eject Failed")

        # Put the current target back in the queue so we can try again
        # This sets up the timeout back to the default. Wonder if we should
        # add some intelligence to make this longer or shorter?
        self.eject_queue.appendleft((self.eject_in_progress_target,
            self.config['eject_timeouts'][self.eject_in_progress_target]))

        # Reset the stuff that showed a current eject in progress
        self.eject_in_progress_target = None
        self.num_balls_ejecting = 0
        self.num_eject_attempts += 1

        if self.config['debug']:
            self.log.info("DEBUG: Eject duration: %ss",
                          time.time() - self.eject_start_time)

        self.machine.events.post('balldevice_' + self.name +
                                 '_ball_eject_failed',
                                 num_attempts=self.num_eject_attempts)

        self._cancel_eject_confirmation()

        if (retry and (not self.config['max_eject_attempts'] or
                self.num_eject_attempts < self.config['max_eject_attempts'])):
            self._do_eject()

        elif force_retry:
            self._do_eject()

        else:
            self._eject_permanently_failed()

    def _eject_permanently_failed(self):
        self.log.warning("Eject failed %s times. Permanently giving up.",
                         self.config['max_eject_attempts'])
        self.machine.events.post('balldevice_' + self.name +
                                 'ball_eject_permanent_failure')

    def _ok_to_receive(self):
        # Post an event announcing that it's ok for this device to receive a
        # ball

        self.machine.events.post('balldevice_' + self.name +
                                 '_ok_to_receive',
                                 balls=self.get_additional_ball_capacity())

    def is_playfield(self):
        """Returns True if this ball device is a Playfield-type device, False if
        it's a regular ball device.

        """
        return self._playfield


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
