""" Contains the base class for ball devices."""
# ball_device.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.tasks import DelayManager
from mpf.system.hardware import Device
from mpf.system.timing import Timing


class BallDevice(Device):
    """Base class for a 'Ball Device' in a pinball machine.

    A ball device  is anything that can hold one or more balls, such as a
    trough, an eject hole, a VUK, a catapult, etc.

    Most (all?) machines will have at least two: the main trough (or wherever
    the balls end up when they drain), and the shooter lane.

    todo:
    whether they're 1-to-1 or virtual?
    trigger recount switch(es)
    manual eject only?
    found_new_ball / or ball count change?
    eject type: 1, all, manual?
    eject firing type: hold a coil, for how long, etc.
    what happens on eject? event on attempt. event on success?

    Parameters
    ----------

    name : string
        How you want to refer to this ball device.

    machine: machine controller instance
        A reference to the machine controller

    hw_dict : dict
        A reference to the hardware dictionary which holds a list of ball
        devices. (Note: this might change)

    config : dict
        A dictionary of settings which specify how this ball device should be
        set up. These settings typically come from the machine config files,
        but really they could come from anywhere. Refer to the config file
        reference for a description of these settings.

    """

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('BallDevice.' + name)
        super(BallDevice, self).__init__(machine, name, config, collection)

        self.delay = DelayManager()

        # set our config defaults
        if 'ball_capacity' not in self.config:
            self.config['ball_capacity'] = 0
        if 'post_eject_delay_check' not in self.config:
            self.config['post_eject_delay_check'] = ".5s"  # todo make optional
        if 'ball_switches' not in self.config:
            self.config['ball_switches'] = None
        if 'ball_count_delay' not in self.config:
            self.config['ball_count_delay'] = "0.5s"
        if 'eject_coil' not in self.config:
            self.config['eject_coil'] = None
        if 'eject_switch' not in self.config:
            self.config['eject_switch'] = None
            # todo what about ones w/o eject switches?
        if 'entrance_switch' not in self.config:
            self.config['entrance_switch'] = None
        if 'jam_switch' not in self.config:
            self.config['jam_switch'] = None
        if 'eject_coil_hold_times' not in self.config:
            self.config['eject_coil_hold_times'] = None  # todo change to list
        if 'eject_target' not in self.config:
            self.config['eject_target'] = None
        if 'confirm_eject_type' not in self.config:
            self.config['confirm_eject_type'] = 'count'  # todo make optional?
        if 'confirm_eject_target' not in self.config:
            self.config['confirm_eject_target'] = None
        if 'eject_type' not in self.config:
            self.config['eject_type'] = 'single'
        if 'player_controlled_eject_tag' not in self.config:
            self.config['player_controlled_eject_tag'] = False
        if 'queue_player_controlled_ejects' not in self.config:
            self.config['queue_player_controlled_ejects'] = False
        if 'feeder_device' not in self.config:
            self.config['feeder_device'] = None
        if 'auto_eject_if_no_event' not in self.config:
            self.config['auto_eject_if_no_event'] = True
        if 'manual_eject' not in self.config:
            self.config['manual_eject'] = False
        if 'eject_attempt_switch' not in self.config:
            self.config['eject_attempt_switch'] = False

        # initialize our variables
        self.num_balls_contained = -999
        # Number of balls currently contained (held) in this device.
        # -999 indicates no count has taken place yet.
        self.num_balls_to_eject = 0
        # Number of balls this device should eject.
        self.num_balls_ejecting = 0
        # Number of balls that are currently in the process of being ejected.
        # When an the eject process starts, the ball is 'transferred' from the
        # num_balls_to_eject to num_balls_ejecting.

        self._failed_eject_event_hander = None
        # Reference to the event handler object which temporarily watches for a
        # ball to enter a device while it's waiting for an eject to be
        # confirmed. We save this object here so we can remove this event
        # handler later once the eject has been confirmed.

        self.event_eject_balls_per_eject = 0
        self.event_eject_balls_remaining = 0
        self.event_eject_queue_requests = False

        self.flag_ok_to_eject = False

        self.num_jam_sw_count = 0
        self.num_balls_desired = 0

        # Now configure the device
        self.configure()

    def configure(self, config=None):
        """Performs the actual configuration of the ball device based on the
        dictionary that was passed to it.

        """

        # Merge in any new changes that were just passed
        if config:
            self.config.update(config)

        self.log.debug("Configuring device with: %s", self.config)

        # now let the fun begin!

        # convert entries that might be multiple items into lists
        # todo should this be automatic based on having a comma in the item?
        self.config['ball_switches'] = self.machine.string_to_list(
            self.config['ball_switches'])

        if not self.config['ball_capacity']:
            self.config['ball_capacity'] = len(self.config['ball_switches'])

        # Register switch handlers for ball switch activity
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch, state=1, ms=0,
                callback=self._ball_switch_handler)
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch, state=0, ms=0,
                callback=self._ball_switch_handler)

        # Configure switch handlers for jam switch activity
        if self.config['jam_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['jam_switch'], state=1, ms=0,
                callback=self._jam_switch_handler)
            # todo do I also need to add inactive and make a smarter
            # handler?

        # Configure switch handlers for entrance switch activity
        if self.config['entrance_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['entrance_switch'], state=1, ms=0,
                callback=self._entrance_switch_handler)
            # todo do I also need to add inactive and make a smarter
            # handler?

        # convert delay times in s or ms to game ticks
        if self.config['post_eject_delay_check']:
            self.config['post_eject_delay_check'] = \
                Timing.time_to_ticks(self.config['post_eject_delay_check'])

        if self.config['ball_count_delay']:
            self.config['ball_count_delay'] = \
                Timing.time_to_ticks(self.config['ball_count_delay'])

        # Register for events
        self.machine.events.add_handler('balldevice_' + self.name +
                                        '_ball_eject_request',
                                        self.eject)

    def get_status(self, request=None):
        """Pass a value to get that status. Or none to get back a dict of the
        full status.

        """

        if request == 'num_balls_contained':
            return self.num_balls_contained
        elif request == 'num_balls_ejecting':
            return self.num_balls_ejecting
        elif request == 'num_balls_to_eject':
            return self.num_balls_to_eject,
        else:
            return {'num_balls_contained': self.num_balls_contained,
                    'num_balls_ejecting': self.num_balls_ejecting,
                    'num_balls_to_eject': self.num_balls_to_eject,
                    }

    def status_dump(self):
        """Dumps the full current status of the device to the log."""

        self.log.debug("+-----------------------------------------+")
        self.log.debug("| num_balls_contained: %s                  |",
                       self.num_balls_contained)
        self.log.debug("| num_balls_ejecting: %s                   |",
                       self.num_balls_ejecting)
        self.log.debug("| num_balls_to_eject: %s                   |",
                       self.num_balls_to_eject)
        self.log.debug("| flag_ok_to_eject: %s                  |",
                       self.flag_ok_to_eject)
        self.log.debug("| num_jam_sw_count: %s                     |",
                       self.num_jam_sw_count)
        self.log.debug("| num_balls_desired: %s                    |",
                       self.num_balls_desired)
        self.log.debug("| num_jam_sw_count: %s                     |",
                       self.num_jam_sw_count)
        self.log.debug("| event_eject_balls_per_eject: %s          |",
                       self.event_eject_balls_per_eject)
        self.log.debug("| event_eject_balls_remaining: %s          |",
                       self.event_eject_balls_remaining)
        self.log.debug("| event_eject_queue_requests: %s        |",
                       self.event_eject_queue_requests)
        self.log.debug("| _failed_eject_event_hander: %s        |",
                       self._failed_eject_event_hander)
        self.log.debug("+-----------------------------------------+")

    def count_balls(self):
        """Counts the balls in the device and processes any new balls that came
        in.

        """

        self.log.debug("Received request to count balls")

        if self.config['ball_switches']:

            ball_count = 0
            ball_change = 0
            previous_balls = self.num_balls_contained
            self.log.debug("Previous number of balls: %s", previous_balls)

            for switch in self.config['ball_switches']:
                if self.machine.switch_controller.is_active(switch):
                    ball_count += 1
                    self.log.debug("Active switch: %s", switch)
            self.log.debug("Counted %s balls", ball_count)

            self.num_balls_contained = ball_count

            # Figure out if we gained or lost any balls since last count?
            if previous_balls == -999:  # This is the first time count
                # No "real" change since we didn't know previous value
                self.log.debug("This was a first time count")
                ball_change = 0
            else:
                ball_change = ball_count - previous_balls
                self.log.debug("Ball count change: %s", ball_change)
                self.machine.ball_controller.ball_contained_count_change(
                    change=ball_change)

            self.set_ok_to_eject()
            self.status_dump()

            if ball_change > 0:
                for i in range(ball_change):  # post once for each ball
                    self.machine.events.post('balldevice_' + self.name +
                                             '_ball_enter')

                    # post the event for this device's switch event tags
                    for tag in self.tags:
                        self.machine.events.post('sw_' + tag)

                    # if there are no events registered, and we have an eject
                    # coil, and auto eject is enabled, then auto eject the new
                    # ball(s) or if we're waiting for a player to eject or if
                    # we have a current eject request

                    if self.config['auto_eject_if_no_event']:
                        if (self.config['eject_coil'] and not (
                                self.num_balls_ejecting or
                                self.num_balls_to_eject or
                                self.event_eject_balls_remaining) and
                                self.machine.ball_controller.num_balls_in_play):
                            self.log.debug("No events registered for this ball"
                                           " entry, or no current ejects, or "
                                           "no events to eject, and a ball is "
                                           "live, so we're ejecting...")
                            self.machine.events.post('balldevice_' + self.name
                                                     + '_ball_eject_request',
                                                     balls=ball_change)

            elif ball_change < 0:  # balls are missing
                # We used to to assume if there was an eject in progress
                # that that's where they went, but now that we have other ways
                # of confirming the eject, we should probably just sit tight
                # and do nothing on this.
                self.log.debug("%s ball(s) missing from device", ball_change)

                if not self.num_balls_ejecting:
                        # Device has randomly lost a ball?
                        self.log.warning("Weird, we're missing a ball but "
                                         "there are no balls ejecting from "
                                         "this device, so let's do a "
                                         "machine-wide full count?")
                        self.machine.ball_controller.ball_update_all_counts()

        else:
            self.log.debug("Received request to count balls, but we don't have"
                           " any ball switches. So we're just returning the"
                           " old count.")
            if self.num_balls_contained == -999:
                self.num_balls_contained = 0

        if self.num_balls_to_eject:
            # If we have balls to eject, eject now
            # todo wonder if there's a way to automate this?
            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_request')

        return self.num_balls_contained

    def is_full(self):
        """Checks to see if this device is "full", meaning it is holding
        either the max number of balls it can hold, or it's holding all the
        known balls in the machine.

        """

        if self.num_balls_contained == self.ball_capacity:
            return True
        elif self.num_balls_contained == \
                self.machine.ball_controller.num_balls_known:
            return True
        else:
            return False

    def _ball_switch_handler(self):
        # We just had a ball switch change.
        # If this device is configured for a delay before counting, wait
        # and/or reset that delay.

        # todo what if this switch is in the process of waiting to confirm an
        # eject? We need to look for and cancel that delay, right?

        # We don't know if we can eject until everything settles
        self.flag_ok_to_eject = False

        if self.config['ball_count_delay']:
            self.log.debug("%s switch just changed state. Will count after "
                           "%s ticks", self.name,
                           self.config['ball_count_delay'])
            self.delay.add(name='ball_count',
                           delay=self.config['ball_count_delay'],
                           callback=self.count_balls)
        else:
            # If no delay is set then just count the balls now
            self.count_balls()

    def _entrance_switch_handler(self):
        # Our entrance switch was hit. This is only used for "virtual" ball
        # counts where we don't have physical switches for each ball held.
        self.log.debug("Ball just hit our entrance switch")

        # todo more to do here:
        # Check to make sure we really are a virtual count device?
        # need to increase contained count
        # should process _ball_count_change

    def _jam_switch_handler(self):
        # The device's jam switch was just activated.
        # This method is typically used with trough devices to figure out if
        # balls fell back in.

        self.num_jam_sw_count += 1
        self.log.debug("Ball device %s jam switch hit. New count: %s",
                       self.name, self.num_jam_sw_count)

    def set_ok_to_eject(self):
        """Checks whether it's ok for this device to eject and sets the flag.

        """
        self.flag_ok_to_eject = True

        # Now let's look for a reason for this not to be true

        if self.config['eject_switch']:  # do we have an eject switch?
            if self.machine.switch_controller.is_inactive(
                    self.config['eject_switch']):  # is it inactive?
                self.flag_ok_to_eject = False
        elif not self.num_balls_contained:  # If not, do we have a ball?
            self.flag_ok_to_eject = False

        # Are we ejecting into a device, and if so, does it have capacity?
        if self.config['eject_target'] == 'balldevice':
            if not self.machine.balldevices[self.config['eject_target']].\
                    is_ok_to_receive():
                self.flag_ok_to_eject = False

    def is_ok_to_receive(self):
        """Checks whether it's ok for this device to receive any balls.

        Returns
        -------

        int : the number of balls this device can receive. 0 = full / not able
        to receive.

        """

        if self.config['ball_capacity'] - self.num_balls_contained < 0:
            self.log.warning("Device reporting more balls contained than its "
                           "capacity.")

        return self.config['ball_capacity'] - self.num_balls_contained

    def stage_ball(self):
        """Used to make sure the device has a ball 'staged' and ready to
        eject.

        """
        self.log.debug("Staging Ball")
        if not self.flag_ok_to_eject:
            self.log.debug("I don't have a ball ready to eject")
            if self.config['feeder_device']:
                feeder = self.machine.balldevices[self.config['feeder_device']]
                # get a ball from the feeder device
                # if feeder is trying to eject, then do nothing.
                if not (feeder.num_balls_to_eject or feeder.num_balls_ejecting):
                    self.log.debug("Requesting ball from feeder device: '%s'",
                                   feeder.name)
                    self.machine.events.post('balldevice_' +
                                             self.config['feeder_device'] +
                                             '_ball_eject_request', balls=1)
                else:
                    self.log.debug("Feeder device '%s' has an eject request "
                                   "already, so we're doing nothing.",
                                   feeder.name)
            else:
                self.log.warning("No feeder device! Stage failed!")
        else:
            self.log.debug("Ball is already staged and ready to go")

    def enable_player_eject(self, balls_per_eject=1, total_balls=1):
        """Enable the ball device to wait for a player-controlled eject.

        A player-controlled eject is where a device is ready to eject a ball
        (or balls), but it's waiting for the player to do hit a button for the
        eject to actually occur. The coil-fired ball launch / plunger is a
        good example of this. Other examples would be the cannons in T2 or
        STTNG, or the free kick in World Cup Soccer 94.

        Parameters
        ----------

        balls_per_eject : int
            How many balls should be ejected each time the player eject event
            occurs.

        total_balls : int
            How many balls should be ejected in total.

        """
        self.log.debug("Waiting for the player to eject.")

        # Add event listeners for any player-controlled eject switches for
        # this ball device
        if self.config['player_controlled_eject_tag']:
            self.enable_eject_event('sw_' +
                self.config['player_controlled_eject_tag'], balls_per_eject)
        else:
            self.log.warning("Received a command to set a player-controlled "
                             "eject, but there's no player_controlled_eject_"
                             "tag specified. So this isn't happening.")

    def enable_eject_event(self, event_name, balls_per_eject=1, total_balls=1,
                           queue=False):
        """Sets up this ball device to eject when the passed event is called.

        Parameters
        ----------

        event_name : str
            The name of the event you want to call the eject()

        balls_per_eject : int
            The number of balls you want to eject each time this event is
            posted.

        total_balls : int
            The total number of balls you want this event to eject. Each time
            it's posted, balls_per_eject will be ejected, up to the total_balls
            specified here.

        queue : bool
            If True, the event can post early (before the device is ready to
            eject) and the eject will happen ASAP. If False, the event will do
            nothing until the device is actually ready to eject.

        """
        self.log.debug("Setting up a handler to eject %s ball(s), in groups of"
                       " %s, when the event '%s' is posted.", total_balls,
                       balls_per_eject, event_name)

        # todo test the queue function
        # make sure this device is ready to eject
        if not self.flag_ok_to_eject:
            self.stage_ball()

        self.machine.events.add_handler(event_name,
                                        handler=self._eject_event_handler)
        self.event_eject_balls_per_eject = balls_per_eject
        self.event_eject_balls_remaining = total_balls
        self.event_eject_queue_requests = queue

    def disable_eject_event(self):
        """Removes the handler that watches events to eject balls from this
        device.

        Todo: Currently this will remove all handlers for this eject event for
        this device. If there's ever a situation where you'd want to watch
        multiple events for the same device and then only remove one of them,
        we'd need to modify this code.
        """
        self.log.debug("Disabling the eject event handlers.")
        self.machine.events.remove_handler(self._eject_event_handler)
        self.event_eject_balls_per_eject = 0
        self.event_eject_balls_remaining = 0

    def _eject_event_handler(self):
        # We received the event that should eject this ball.

        if self.flag_ok_to_eject or self.event_eject_queue_requests:
            # proceed with eject because either the device is ready, or we're
            # queueing eject requests.

            eject_this_round = 0
            if self.event_eject_balls_remaining > \
                    self.event_eject_balls_per_eject:
                eject_this_round = self.event_eject_balls_per_eject
            else:
                eject_this_round = self.event_eject_balls_remaining
            self.event_eject_balls_remaining -= eject_this_round

            if self.event_eject_balls_remaining <= 0:
                self.disable_eject_event()

            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_request',
                                     balls=eject_this_round)

        # if we're not queueing eject requests and the device is not ready to
        # eject, then we're going to end up here and nothing will have happened

    def stop(self):
        """Stops all activity in a device.

        Cancels all pending eject requests. Cancels eject confirmation checks.

        """
        self.log.debug("Stopping all activity via stop()")
        self.num_balls_ejecting = 0
        self.num_balls_to_eject = 0
        self.num_jam_sw_count = 0

        self.cancel_eject_confirmation()
        self.count_balls()  # need this since we're canceling the eject conf

    def eject(self, balls=0, force=False):
        """Eject a ball from the device

        Parameters
        ----------

        balls : int
            Number of balls to eject. Default is 0. If this value is zero, this
            method will still process existing ejecting balls or balls to
            eject.

        force : bool
            Forces the device to fire the eject coil, even if it thinks it's
            not ok to eject.

        """
        self.log.debug("Received eject request. Num balls: %s Force: %s",
                       balls, force)
        self.num_balls_to_eject += balls
        self.status_dump()

        if self.num_balls_ejecting:
            # if we have an eject in progress, don't do anything more here.
            # we'll loop back through to pick up any additional balls later.
            self.log.debug("Received eject request, but since there's a "
                           "current eject in progress, we're doing nothing")
            return

        elif self.num_balls_to_eject:

            if not self.flag_ok_to_eject:
                self.stage_ball()
                # We can safely return here because if the stage_ball()
                # works then we'll end up with a new ball in this device,
                # which in turn will call eject()
                return

            if (self.flag_ok_to_eject and not self.num_balls_ejecting) or\
                    (force is True):
                # if it's ok to eject, and we're not in the process of
                # ejecting or if force=True, then let's eject now

                if self.config['eject_type'] == 'single':
                    # this device ejects a single ball at a time
                    balls_to_eject = 1
                else:
                    # this device ejects all the balls at once
                    balls_to_eject = self.num_balls_to_eject

                self.num_balls_ejecting += balls_to_eject
                self.num_balls_to_eject -= balls_to_eject

                if self.config['jam_switch']:
                    self.num_jam_sw_count = 0
                    if self.machine.switch_controller.is_active(
                            self.config['jam_switch']):
                        self.num_jam_sw_count += 1
                        # catches if the ball is blocking the switch to
                        # begin with, todo we have to get smart here

                self.machine.events.post('balldevice_' + self.name +
                                         '_ball_eject_attempt')
                # todo if the event queue is busy, this event will be
                # queued, yet the coil pulse happens now. Is that ok?

                if self.config['eject_coil']:
                    self._setup_eject_confirmation()
                    self.machine.coils[self.config['eject_coil']].pulse()
                    # todo add support for hold coils with var. release times

                    # todo cancel event based ejects?

                    self.num_balls_contained -= balls_to_eject
                    self.machine.ball_controller.ball_contained_count_change(
                        change=-balls_to_eject)

                else:  # No eject coil, so this is old-school manual style
                    self._setup_eject_confirmation(style='surprise')

    def _setup_eject_confirmation(self, style=None):
        # Called right after an eject coil is fired to confirm the eject
        # The exact method of confirmation depends on how this ball device
        # has been configured.

        # This method will also install a handler on the device doing the eject
        # to watch to see if the ball accidentally fell back in before the
        # eject was confirmed.

        # Parameter style='surprise' means this is for a manual plunger where
        # the machine has no advanced warning that the eject is coming.

        self.log.debug("Setting up the eject confirmation")

        if self.config['confirm_eject_type'] == 'device':
            # watch for ball entry event on that device
            # Note this must be higher priority than the failed eject handler
            self.machine.events.add_handler(
                'balldevice_' + self.config['confirm_eject_target'] +
                '_ball_enter', self.eject_success, 2)

        elif self.config['confirm_eject_type'] == 'switch':
            # watch for that switch to activate momentarily
            # todo add support for a timed switch here
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['confirm_eject_target'],
                callback=self._eject_success,
                state=1, ms=0)

        elif self.config['confirm_eject_type'] == 'event':
            # watch for that event
            self.machine.events.add_handler(
                self.config['confirm_eject_target'], self._eject_success)

        elif self.config['confirm_eject_type'] is 'count' or\
                (self.config['confirm_eject_type'] is 'playfield' and
                 self.machine.ball_controller.num_balls_in_play > 0):
            # We need to set a delay to confirm the eject. We can go right
            # into the eject_sucess from here because if the ball falls
            # back in, the ball switch handler will cause a recount and
            # figure it out. We only do this if the device is configured to
            # confirm eject via a 'count,' or if it's set to confirm eject
            # via the playfield but there's already a ball in play.
            self.delay.add(name=self.name + '_confirm_eject',
                           event_type=None,
                           delay=self.config['post_eject_delay_check'],
                           handler=self.count_balls)

        elif self.config['confirm_eject_type'] == 'playfield':
            # This option is only used with 'playfield' when no balls are live
            self.machine.events.add_handler('sw_ballLive',
                                            self._eject_success)

        else:
            # If there's no confirm eject type specified, then we'll just
            # confirm it right away.
            self._eject_success()
            return

        # Watch to make sure the ejecting ball didn't fall back in
        # Note this has to be lower priority than the success handler
        # Why?
        self._failed_eject_event_hander = self.machine.events.add_handler(
            'balldevice_' + self.name + '_ball_enter', self.eject_failed, 1)

    def cancel_eject_confirmation(self):
        """Cancels and removes the checks that were put in place to confirm a
        ball eject from this device.

        This method is used in two ways:
            * When the eject has been confirmed, it's called to remove any
            checks that had been setup.
            * If something "big" happens and the machine has to cancel
            everything (tilt, reset, etc.), then the machine controller can
            loop through every ball device and call these one-by-one.

        """

        # Remove any event watching for success
        self.machine.events.remove_handler(self._eject_success)

        # Remove the event handler watching for the ball to fall back in
        self.machine.events.remove_handler(self.eject_failed)
        self._failed_eject_event_hander = None

        # Remove any delays
        self.delay.remove(self.name + '_confirm_eject')

        # Remove any switch handlers
        self.machine.switch_controller.remove_switch_handler(
            switch_name=self.config['confirm_eject_target'],
            callback=self._eject_success,
            state=1, ms=0)

    def _eject_success(self, balls_ejected=1):
        # We got an eject success for this device.
        # Since there are many ways we can get here, let's first make sure we
        # actually had an eject in progress
        if self.num_balls_ejecting:
            self.log.debug("Confirmed %s ball(s) ejected successfully",
                           balls_ejected)

            self.num_balls_ejecting -= balls_ejected
            #if self.num_balls_ejecting > self.num_balls_to_eject:
            #    self.num_balls_ejecting = self.num_balls_to_eject
            # Commented the above because it shouldn't happen. If it does it's
            # because there's a root cause bug somewhere else we should find.
            self.num_jam_sw_count = 0  # todo add if we're using this

            # todo cancel post eject check delay
            # todo was inc live?

            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_success',
                                     balls_ejected=balls_ejected)
            # need to add num balls to eject confirm

        else:
            self.log.warning("We got to '_eject_success' but no eject was in "
                             "progress. Just FYI that something's weird.")

        # if there are no more ejecting balls in progress, cancel the checks
        if self.num_balls_ejecting < 1:
            self.cancel_eject_confirmation()

        # if we still have balls to eject, then loop through that
        if self.num_balls_to_eject:
            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_request')
            # no num here as we don't want to increase the current count

    def eject_failed(self, balls=0):
        """An eject failed.

        Parameter
        ---------

        balls : int
            How many balls were attempted to be ejected but failed. Default of
            0 is a placeholder which means all of them failed.

        Typically this happens when a ball enters the device while its
        num_balls_ejecting variable is > 0. (If the eject was successful, that
        variable would have been reset.)

        """
        # todo audit the number of failed ejects for this device

        # todo do we really need to track the number of ejecting balls that
        # failed? I mean it's either one, or all, right? Can we really have
        # multiple ejecting balls and only have some of them fail? How is it
        # not always all or nothing?

        self.cancel_eject_confirmation()

        # "roll back" the ejecting ball count
        if balls:
            self.num_balls_to_eject += balls
            self.num_balls_ejecting -= balls
        else:
            self.num_balls_to_eject += self.num_balls_ejecting
            self.num_balls_ejecting = 0

        if self.num_balls_ejecting < 0:
            self.log.warning("eject_failed() is trying to make "
                             "num_balls_ejecting negative. Something is weird")

        # try again
        self.machine.events.post('balldevice_' + self.name +
                                 '_ball_eject_request')

        # todo should we count the number of tries and give up at some point?
        # if so, we'll post the eject failed, but then what? Man, the machine
        # might be kind of hosed at that point.

    def eject_all(self, increment_live=False):
        """Ejects all balls from the device."""

        self.log.debug("Ejecting all balls")
        self.machine.events.post('balldevice_' + self.name +
                                 '_ball_eject_request',
                                 balls=self.num_balls_contained)
        # todo implement inc live

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