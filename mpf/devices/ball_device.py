""" Contains the base class for ball devices."""
# ball_device.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from collections import deque
import time

from mpf.system.tasks import DelayManager
from mpf.system.device import Device
from mpf.system.timing import Timing
from mpf.system.config import Config


class BallDevice(Device):
    """Base class for a 'Ball Device' in a pinball machine.

    A ball device is anything that can hold one or more balls, such as a
    trough, an eject hole, a VUK, a catapult, etc.

    Args: Same as Device.
    """

    config_section = 'ball_devices'
    collection = 'ball_devices'
    class_label = 'ball_device'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super(BallDevice, self).__init__(machine, name, config, collection,
                                         validate=validate)

        self.delay = DelayManager()

        if self.config['ball_capacity'] is None:
            self.config['ball_capacity'] = len(self.config['ball_switches'])

        # initialize variables

        self.balls = 0
        """Number of balls currently contained (held) in this device."""

        self.eject_queue = deque()
        """ Queue of the list of eject targets (ball devices) for the balls this
        device is trying to eject.
        """

        self.num_eject_attempts = 0
        """ Counter of how many attempts to eject the current ball this device
        has tried. Eventually it will give up.
        """
        # todo log attemps more than one?

        self.eject_in_progress_target = None
        """The ball device this device is currently trying to eject to."""

        self.num_jam_switch_count = 0
        """How many times the jam switch has been activated since the last
        successful eject.
        """

        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize)

        self.machine.events.add_handler('machine_reset_phase_2',
                                        self._initialize2)

        self.machine.events.add_handler('machine_reset_phase_3',
                                        self._initialize3)


        self.num_balls_ejecting = 0
        """ The number of balls that are currently in the process of being
        ejected. This is either 0, 1, or whatever the balls was
        for devices that eject all their balls at once.
        """

        self.mechanical_eject_in_progress = False
        """How many balls are waiting for a non-controlled (e.g. spring
        plunger) eject.
        """

        self.waiting_for_eject_trigger = False
        """Whether this device is waiting for an event to trigger the eject.
        """

        self._source_devices = []

        self._is_connected_to_ball_source_state = None

        self._blocked_eject_attempts = deque()

        self.pending_eject_event_keys = set()

        self.hold_release_in_progress = False

        self._state = "invalid"

        self._incoming_balls = deque()

        self._source_ejecting_balls = 0

        self.machine.events.add_handler('init_phase_2',
                                        self.configure_eject_targets)

        if (self.config['confirm_eject_type'] == "switch" and
                not self.config['confirm_eject_switch']):
            raise AssertionError("When using confirm_eject_type switch you " +
                                 "to specify a confirm_eject_switch")

    # Logic and dispatchers

    def _switch_state(self, new_state, **kwargs):
        # TODO: check if transition is legal
        if new_state == self._state:
            self.log.debug("Tried to switch state. But already in state %s",
                           new_state)
            return


        self._state = new_state

        self.log.debug("Switching to state %s", new_state)

        method_name = "_state_" + self._state + "_start"
        if not hasattr(self, method_name):
            raise AssertionError("Went to invalid state %s", self._state)
        method = getattr(self, method_name, lambda *args: None)
        method(**kwargs)

    def _counted_balls(self, balls, **kwargs):
        method_name = "_state_" + self._state + "_counted_balls"
        method = getattr(self, method_name, lambda *args: None)
        method(balls)

    def _target_ready(self, target, **kwargs):
        if self._state == "wait_for_eject":
            self._state_wait_for_eject_start()

    # State idle
    def _handle_eject_queue(self):
        if self.eject_queue:
            self.num_eject_attempts = 0
            self.num_jam_switch_count = 0
            if self.balls > 0:
                return self._switch_state("wait_for_eject")
            else:
                # only request ball if we have no incomings
                if not len(self._incoming_balls) and not self._source_ejecting_balls:
                    if self.debug:
                        self.log.debug("Don't have any balls. Requesting one.")
                    self._request_one_ball()

                return self._switch_state("waiting_for_ball")



    def _state_idle_start(self):
        # Lets count the balls to see if we received ball in the meantime
        # before we start an eject with wrong initial count
        self._idle_counted = False
        return self._count_balls()

    def _state_idle_eject_request(self):
        # make sure ball switches are stable and do the eject after ball count
        return self._count_balls()

    def _state_idle_counted_balls(self, balls):
        self._idle_counted = True
        if self.balls < 0:
            raise AssertionError("Ball count went negative")

        if self.balls > balls:
            # balls went missing. we are idle
            missing_balls = self.balls - balls
            self.balls = balls
            return self._switch_state("missing_balls",
                                balls=missing_balls)
        elif self.balls < balls:
            # unexpected balls
            unexpected_balls = balls-self.balls
            self.balls = balls
            self._handle_new_balls(balls=unexpected_balls)

        # handle timeout incoming balls
        missing_balls = 0
        while len(self._incoming_balls) and self._incoming_balls[0][0] <= time.time():
            self._incoming_balls.popleft()
            missing_balls += 1
        if missing_balls > 0:
            # TODO: handle this more list lost_balls. we may have to cancel ejects
            return self._switch_state("missing_balls",
                                balls=missing_balls)

        if self.get_additional_ball_capacity():
            # unblock blocked source_device_eject_attempts
            if not self.eject_queue or not self.balls:
                if self._blocked_eject_attempts:
                    (queue, source) = self._blocked_eject_attempts.popleft()
                    queue.clear()
                    return self._switch_state("waiting_for_ball")

                self._ok_to_receive()


        # No new balls
        # In idle those things can happen:
        # 1. A ball enter (via ball switches -> will call this method again)
        # 2. We get an eject request (via _eject_request)
        # 3. Sb wants to send us a ball (via _source_device_eject_attempt)

        # We might already have an eject queue. If yes go to eject
        return self._handle_eject_queue()


    def _handle_unexpected_balls(self, balls):
        self.machine.events.post('sw_' + self.config['captures_from'] + "_active")
        self.delay.add(callback=self._handle_unexpected_balls2, ms=0, balls=balls)

    def _handle_unexpected_balls2(self, balls):
        self.log.debug("Received %s unexpected balls", balls)
        self.machine.events.post('balldevice_captured_from_' +
                                  self.config['captures_from'],
                                  balls=balls)

    def _handle_new_balls(self, balls):
        while len(self._incoming_balls) > 0 and balls > 0:
            balls -= 1
            self._incoming_balls.popleft()

        if balls > 0:
            self._handle_unexpected_balls(balls)

        self.log.debug("Processing %s new balls", balls)
        self.machine.events.post_relay('balldevice_' + self.name +
                                       '_ball_enter',
                                        balls=balls,
                                        device=self,
                                        callback=self._balls_added_callback)


    def _state_lost_balls_start(self, balls):
        # Request a new ball depending on setting
        if  self.config['ball_missing_action'] == "retry":
            self.log.debug("Lost %s balls during eject. Will retry the "
                           "eject.", balls)
            self.eject_failed()
        else:
            self.log.debug("Lost %s balls during eject. Will ignore the "
                           "loss.", balls)
            self.eject_failed(retry=False)
            self.machine.events.post('balldevice_' + self.name + '_ball_lost',
                balls=abs(balls), target=self.eject_in_progress_target)


        self._balls_missing(balls)


        # Reset target
        self.eject_in_progress_target = None



        return self._switch_state("idle")


    def _state_missing_balls_start(self, balls):
        if self.config['mechanical_eject']:
            # if the device supports mechanical eject we assume it was one
            self.mechanical_eject_in_progress = True
            # TODO: use target from setup_player_controlled_eject
            self.eject_in_progress_target = self.config['eject_targets'][0]
            self.num_balls_ejecting = 1
            #self.eject_queue.append((target, 0))
            self._do_eject_attempt()
            return self._switch_state("ball_left")

        self._balls_missing(balls)

        return self._switch_state("idle")

    def _state_waiting_for_ball_start(self):
        # This can happen
        # 1. ball counts can change (via _counted_balls)
        # 2. if mechanical_eject and the ball leaves source we go to
        #    waiting_for_ball_mechnical
        pass

    def _state_waiting_for_ball_counted_balls(self, balls):
        if self.balls > balls:
            # We dont have balls. How can that happen?
            raise AssertionError("We dont have balls but lose one!")
        elif self.balls < balls:
            # Go to idle state
            return self._switch_state("idle")

        # Default: wait

    def _state_waiting_for_ball_mechanical_start(self):
        # This can happen
        # 1. ball counts can change (via _counted_balls)
        # 2. eject can be confirmed
        # 2. eject of source can fail
        self.eject_in_progress_target = self.config['eject_targets'][0]
        self.num_balls_ejecting = 1
        self.mechanical_eject_in_progress = True
        #self._setup_eject_confirmation(self.eject_in_progress_target)
        self._inform_target_about_incoming_ball(self.eject_in_progress_target)
        self._do_eject_attempt()


    def _state_waiting_for_ball_mechanical_counted_balls(self, balls):
        if self.balls > balls:
            # We dont have balls. How can that happen?
            raise AssertionError("We dont have balls but lose one!")
        elif self.balls < balls:
            self._cancel_incoming_ball_at_target(self.eject_in_progress_target)
            self._cancel_eject_confirmation()

            # Go to idle state
            return self._switch_state("idle")

        # Default: wait

    def add_incoming_ball(self, source):
        # TODO: replace by an event
        timeout = 60
        self._incoming_balls.append((time.time() + timeout, source))
        self.delay.add(ms=timeout * 1000, callback=self._timeout_incoming)

        if self._state == "waiting_for_ball" and self.config['mechanical_eject']:
            self._switch_state("waiting_for_ball_mechanical")


    def _timeout_incoming(self):
        self.log.debug("Handling timeouts of incoming balls")
        if len(self._incoming_balls) and self._state == "idle":
            self._count_balls()

    def remove_incoming_ball(self, source):
        # TODO: replace by an event
        self._incoming_balls.popleft()

    def _state_ball_left_start(self):

        # TODO: handle entry switch here -> definitely new ball
        # TODO: handle jam switch here -> ball did not leave
        if self.config['jam_switch']:
            self.num_jam_switch_count = 0
            if self.machine.switch_controller.is_active(
                    self.config['jam_switch'].name):
                self.num_jam_switch_count += 1
                # catches if the ball is blocking the switch to
                # begin with, todo we have to get smart here
        self.machine.events.post('balldevice_' + self.name + '_ball_left',
                                 balls=self.num_balls_ejecting,
                                 target=self.eject_in_progress_target,
                                 num_attempts=self.num_eject_attempts)

        # TODO: do this also for player controlled eject
        if self.config['confirm_eject_type'] == 'target':
            self._inform_target_about_incoming_ball(self.eject_in_progress_target)



    def _state_wait_for_eject_start(self):
        target = self.eject_queue[0][0]
        if target.get_additional_ball_capacity():
            return self._switch_state("ejecting")

    def _state_ejecting_start(self):
        self.eject_in_progress_target, self.mechanical_eject_in_progress, self.trigger_event = (self.eject_queue.popleft())
        if self.debug:
            self.log.debug("Setting eject_in_progress_target: %s, " +
                           "mechanical: %s, trigger_events %s",
                           self.eject_in_progress_target.name,
                           self.mechanical_eject_in_progress,
                           self.trigger_event)

        self.num_eject_attempts += 1

        self.num_balls_ejecting = 1

        self._do_eject_attempt()


    def _do_eject_attempt(self):
        self.machine.events.post_queue('balldevice_' + self.name +
                                 '_ball_eject_attempt',
                                 balls=self.num_balls_ejecting,
                                 target=self.eject_in_progress_target,
                                 source=self,
                                 mechanical_eject=self.mechanical_eject_in_progress,
                                 num_attempts=self.num_eject_attempts,
                                 callback=self._perform_eject)


    def _state_failed_eject_start(self):
        # TODO: either do this check in eject_failure or always go to this state
        # handle retry limit
        if (self.config['max_eject_attempts'] != 0 and
            self.num_eject_attempts > self.config['max_eject_attempts']):
            self._eject_permanently_failed()
            # What now? Ball is still in device or switch just broke. At least
            # we are unable to get rid of it
            return self._switch_state("broken")

        # TODO: timer for retry

        # ball did not leave. eject it again
        return self._switch_state("ejecting")

    def _state_failed_confirm_start(self):
        # count balls to see if the ball returns
        self._count_balls()
        timeout = self.config['ball_missing_timeouts'][self.eject_in_progress_target]
        self.delay.add(name='ball_missing_timeout',
                       ms=timeout,
                       callback=self._ball_missing_timout)

    def _state_failed_confirm_counted_balls(self, balls):
        if self.balls > balls:
            # we lost even more balls? if the do not come back until timeout
            # we will go to state "missing_balls" and forget about the first
            # one. Afterwards, we will go to state "idle" and it will handle
            # all additional missing balls
            # TODO: can we use state missing_balls here?
            pass
        elif self.balls < balls:
            # TODO: check if entry switch was active.
            # ball probably returned
            self._cancel_incoming_ball_at_target(self.eject_in_progress_target)
            self.balls += 1
            self.eject_failed()
            self._switch_state("ejecting")

    def _state_eject_confirmed_start(self):
        self.eject_in_progress_target = None
        return self._switch_state("idle")


    def _ball_missing_timout(self):
        if self._state != "failed_confirm":
            raise AssertionError("Invalid state " + self._state)

        if not self.config['confirm_eject_type'] == 'switch':
            self._cancel_incoming_ball_at_target(self.eject_in_progress_target)

        # We are screwed now!
        # TODO: this is not missing. its lost balls. separate!
        return self._switch_state("lost_balls",
                    balls=1)

    @property
    def num_balls_ejectable(self):
        """How many balls are in this device that could be ejected."""
        return self.balls

        # todo look at upstream devices

    def configure_eject_targets(self, config=None):
        new_list = list()

        for target in self.config['eject_targets']:
            new_list.append(self.machine.ball_devices[target])

        self.config['eject_targets'] = new_list

    def _source_device_eject_attempt(self, balls, target, source, queue, **kwargs):
        if target != self:
            return

        if not self.is_ready_to_receive():
            # block the attempt until we are ready again
            self._blocked_eject_attempts.append((queue, source))
            queue.wait()
            return

        # track ejects
        self._source_ejecting_balls += 1

    def _source_device_eject_failed(self, balls, target, retry, **kwargs):
        if target != self:
            return

        # track ejects
        self._source_ejecting_balls -= 1

        if self._state == "waiting_for_ball_mechanical":
            self._cancel_incoming_ball_at_target(self.eject_in_progress_target)
            self._cancel_eject_confirmation()
            if not retry:
                self.eject_queue.popleft()
                # TODO: ripple this to the next device
                return self._switch_state("idle")
            else:
                return self._switch_state("waiting_for_ball")

        if self._state == "waiting_for_ball" and not retry:
            self.eject_queue.popleft()
            # TODO: ripple this to the next device
            return self._switch_state("idle")

    def _source_device_eject_success(self, balls, target, **kwargs):
        if target != self:
            return

        # track ejects
        self._source_ejecting_balls -= 1


    def _initialize(self):
        # convert names to objects

        # make sure the eject timeouts list matches the length of the eject targets
        if (len(self.config['eject_timeouts']) <
                len(self.config['eject_targets'])):
            self.config['eject_timeouts'] += ["10s"] * (
                len(self.config['eject_targets']) -
                len(self.config['eject_timeouts']))

        if (len(self.config['ball_missing_timeouts']) <
                len(self.config['eject_targets'])):
            self.config['ball_missing_timeouts'] += ["20s"] * (
                len(self.config['eject_targets']) -
                len(self.config['ball_missing_timeouts']))


        timeouts_list = self.config['eject_timeouts']
        self.config['eject_timeouts'] = dict()

        for i in range(len(self.config['eject_targets'])):
            self.config['eject_timeouts'][self.config['eject_targets'][i]] = (
                Timing.string_to_ms(timeouts_list[i]))

        timeouts_list = self.config['ball_missing_timeouts']
        self.config['ball_missing_timeouts'] = dict()

        for i in range(len(self.config['eject_targets'])):
            self.config['ball_missing_timeouts'][self.config['eject_targets'][i]] = (
                Timing.string_to_ms(timeouts_list[i]))
        # End code to create timeouts list -------------------------------------

        # Register switch handlers with delays for entrance & exit counts
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                ms=self.config['entrance_count_delay'],
                callback=self._switch_changed)
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=0,
                ms=self.config['exit_count_delay'],
                callback=self._switch_changed)

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

        # handle hold_coil activation when a ball hits a switch
        for switch in self.config['hold_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch.name, state=1,
                ms=0,
                callback=self.hold)



        # Configure event handlers to watch for target device status changes
        for target in self.config['eject_targets']:
            # Target device is requesting a ball

            self.machine.events.add_handler(
                'balldevice_{}_ball_request'.format(target.name),
                self._eject_request, target=target)


            # Target device is now able to receive a ball
            self.machine.events.add_handler(
                'balldevice_{}_ok_to_receive'.format(target.name),
                self._target_ready, target=target)

        # Get an initial ball count
        self.count_balls(stealth=True)

    def _initialize2(self):
        # Watch for ejects targeted at us
        for device in self.machine.ball_devices:
            for target in device.config['eject_targets']:
                if target.name == self.name:
                    self._source_devices.append(device)
                    if self.debug:
                        self.log.debug("EVENT: {} to {}".format(device.name,
                                       target.name))
                    self.machine.events.add_handler(
                        'balldevice_{}_ball_eject_failed'.format(device.name),
                        self._source_device_eject_failed)

                    self.machine.events.add_handler(
                        'balldevice_{}_ball_eject_attempt'.format(device.name),
                        self._source_device_eject_attempt)

                    self.machine.events.add_handler(
                        'balldevice_{}_ball_eject_success'.format(device.name),
                        self._source_device_eject_success)

                    break


    def _initialize3(self):
        if (not self.is_connected_to_ball_source() and
            self.config['ball_missing_action'] == "retry"):
            raise AssertionError("Cannot use retry as ball_missing_action " +
                            "when not connected to a ball source")

        self._switch_state("idle")

    def get_status(self, request=None): # pragma: no cover
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

    def status_dump(self): # pragma: no cover
        """Dumps the full current status of the ball device to the log."""

        if self.debug:
            self.log.debug("+-----------------------------------------+")
            self.log.debug("| balls: {}".format(
                self.balls).ljust(42) + "|")
            self.log.debug("| eject_in_progress_target: {}".format(
                self.eject_in_progress_target).ljust(42) + "|")
            self.log.debug("| num_balls_ejecting: {}".format(
                self.num_balls_ejecting).ljust(42) + "|")
            self.log.debug("| num_jam_switch_count: {}".format(
                self.num_jam_switch_count).ljust(42) + "|")
            self.log.debug("| num_eject_attempts: {}".format(
                self.num_eject_attempts).ljust(42) + "|")
            self.log.debug("| eject queue: {}".format(
                self.eject_queue).ljust(42) + "|")
            self.log.debug("| mechanical_eject_in_progress: {}".format(
                self.mechanical_eject_in_progress).ljust(42) + "|")
            self.log.debug("+-----------------------------------------+")

    def _switch_changed(self, **kwargs):
        self._count_balls()

    def count_balls(self, **kwargs):
        # deprecated
        return self.balls

    def _count_balls(self, **kwargs):
        if self.debug:
            self.log.debug("Counting balls")

        if self.config['ball_switches']:
            try:
                balls = self._count_ball_switches()
            except ValueError:
                # This happens when switches are not stable. We will be called again!
                return
        else:
            balls = self.balls

        # current status handler will handle the new count (or ignore it)
        self._counted_balls(balls)

    def _count_ball_switches(self):
        # only count. do not change any state here!
        ball_count = 0

        for switch in self.config['ball_switches']:
            valid = False
            if self.machine.switch_controller.is_active(switch.name,
                    ms=self.config['entrance_count_delay']):
                ball_count += 1
                valid = True
                if self.debug:
                    self.log.debug("Confirmed active switch: %s", switch.name)
            elif self.machine.switch_controller.is_inactive(switch.name,
                    ms=self.config['exit_count_delay']):
                if self.debug:
                    self.log.debug("Confirmed inactive switch: %s", switch.name)
                valid = True

            if not valid:  # one of our switches wasn't valid long enough
                # recount will happen automatically after the time passes
                # via the switch handler for count
                if self.debug:
                    self.log.debug("Switch '%s' changed too recently. "
                                   "Aborting count & returning previous "
                                   "count value", switch.name)
                raise ValueError('Count not stable yet. Run again!')

        if self.debug:
            self.log.debug("Counted %s balls", ball_count)

        return ball_count

    def _balls_added_callback(self, balls, **kwargs):
        # If we still have balls here, that means that no one claimed them, so
        # essentially they're "stuck." So we just eject them... unless this
        # device is tagged 'trough' in which case we let it keep them.
        if balls and 'trough' not in self.tags:
            self._eject_request(balls)

    def _balls_missing(self, balls):
        # Called when ball_count finds that balls are missing from this device
        if self.debug:
            self.log.debug("%s ball(s) missing from device. Mechanical eject?"
                           " %s", abs(balls),
                           self.mechanical_eject_in_progress)

        self.machine.events.post('balldevice_{}_ball_missing'.format(
            abs(balls)))
        self.machine.events.post('balldevice_ball_missing',
            balls=abs(balls))

        # add ball to default target
        self.machine.ball_devices[self.config['ball_missing_target']].balls += balls

    def is_full(self):
        """Checks to see if this device is full, meaning it is holding either
        the max number of balls it can hold, or it's holding all the known
        balls in the machine.

        Returns: True or False

        """
        if (self.config['ball_capacity'] and
                    self.balls >= self.config['ball_capacity']):
            return True
        elif self.balls >= self.machine.ball_controller.num_balls_known:
            return True
        else:
            return False

    def _jam_switch_handler(self):
        # The device's jam switch was just activated.
        # This method is typically used with trough devices to figure out if
        # balls fell back in.

        self.num_jam_switch_count += 1
        if self.debug:
            self.log.debug("Ball device %s jam switch hit. New count: %s",
                           self.name, self.num_jam_switch_count)

    def _entrance_switch_handler(self):
        # A ball has triggered this device's entrance switch

        if not self.config['ball_switches']:
            if self.is_full():
                self.log.warning("Device received balls but is already full. "
                                 "Ignoring!")
                return

            self.balls += 1
            self._handle_new_balls(1)

    def is_ready_to_receive(self):
        return ((self._state == "idle" and self._idle_counted) or (self._state == "waiting_for_ball")
                and self.balls < self.config['ball_capacity'])

    def get_real_additional_capacity(self):
        if self.config['ball_capacity'] - self.balls < 0:
            self.log.warning("Device reporting more balls contained than its "
                             "capacity.")

        return self.config['ball_capacity'] - self.balls


    def get_additional_ball_capacity(self):
        # TODO: deprecated. Name is missleading
        """Returns an integer value of the number of balls this device can
            receive. A return value of 0 means that this device is full and/or
            that it's not able to receive any balls at this time due to a
            current eject_in_progress.

        """
        capacity = self.get_real_additional_capacity()
        capacity -= len(self._incoming_balls)
        capacity -= self.num_balls_ejecting
        if capacity < 0:
            return 0
        else:
            return capacity

    def is_connected_to_ball_source(self):
        if "drain" in self.tags:
            return True

        if self._is_connected_to_ball_source_state == None:
            self._is_connected_to_ball_source_state = False
            for source in self._source_devices:
                if source.is_connected_to_ball_source():
                    self._is_connected_to_ball_source_state = True
                    break
        return self._is_connected_to_ball_source_state

    def _request_one_ball(self):
        # this will request a ball. no matter what
        self.machine.events.post('balldevice_' + self.name +
                                 '_ball_request', balls=1)


    def request_ball(self, balls=1):
        """Request that one or more balls is added to this device.

        Args:
            balls: Integer of the number of balls that should be added to this
                device. A value of -1 will cause this device to try to fill
                itself.
        """
        if self.debug:
            self.log.debug("In request_ball. balls: %s", balls)

        # How many balls are we requesting?
        remaining_capacity = (self.config['ball_capacity'] -
                              self.balls)

        if remaining_capacity < 0:
            remaining_capacity = 0

        # Figure out how many balls we can request
        if balls == -1 or balls > remaining_capacity:
            balls = remaining_capacity

        if not balls:
            return False

        if self.debug:
            self.log.debug("Requesting Ball(s). Balls=%s", balls)

        for i in range(balls):
            self._request_one_ball()

        return balls

    def stop(self, **kwargs):
        # TODO: convert
        raise AssertionError("broken")
        """Stops all activity in this device.

        Cancels all pending eject requests. Cancels eject confirmation checks.

        """
        if self.debug:
            self.log.debug("Stopping all activity via stop()")
        self.eject_in_progress_target = None
        self.eject_queue = deque()
        self.num_jam_switch_count = 0

        # todo jan19 anything to add here?

        self._cancel_eject_confirmation()
        self.count_balls()  # need this since we're canceling the eject conf

    def setup_player_controlled_eject(self, balls=1, target=None,
                                      trigger_event=None):
        # TODO: handle trigger_event

        if self.debug:
            self.log.debug("Setting up player-controlled eject. Balls: %s, "
                           "Target: %s, trigger_event: %s",
                           balls, target, trigger_event)

        if not self.config['mechanical_eject']:
            self.eject(balls, target=target)
            return


        assert balls == 1

        self.eject_queue.append((target, True, trigger_event))
        self._count_balls()

    def _eject_request(self, balls=1, target=None, **kwargs):
        # TODO: make sure only one device ejects
        if balls:
            self.eject(balls, target, **kwargs)

    def eject(self, balls=1, target=None, **kwargs):
        if not target:
            target = self.config['eject_targets'][0]

        timeout = self.config['eject_timeouts'][target]

        if self.debug:
            self.log.debug('Adding %s ball(s) to the eject_queue.',
                           balls)


        # add request to queue
        for i in range(balls):
            self.eject_queue.append((target, False, None))

        if self.debug:
            self.log.debug('Queue %s.', self.eject_queue)

        # call status handler if any
        method_name = "_state_" + self._state + "_eject_request"
        method = getattr(self, method_name, lambda: None)
        method()

    def eject_all(self, target=None):
        """Ejects all the balls from this device

        Args:
            target: The string or BallDevice target for this eject. Default of
                None means `playfield`.

        Returns:
            True if there are balls to eject. False if this device is empty.

        """
        if self.debug:
            self.log.debug("Ejecting all balls")
        if self.balls > 0:
            self.eject(balls=self.balls, target=target)
            return True
        else:
            return False

    def _eject_status(self):
        if self.debug:

            if self.machine.tick_num % 10 == 0:
                try:
                    self.log.debug("DEBUG: Eject duration: %ss. Target: %s",
                                  round(time.time()-self.eject_start_time, 2),
                                  self.eject_in_progress_target.name)
                except AttributeError:
                    self.log.debug("DEBUG: Eject duration: %ss. Target: None",
                                  round(time.time()-self.eject_start_time, 2))

    def _ball_left_device(self, balls, **kwargs):
        assert balls == 1
        assert self._state == "ejecting"
        # remove handler
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self._ball_left_device,
                state=0)
        self.balls -= 1

        self.log.debug("Ball left. New count %s", self.balls)
        self._switch_state("ball_left")

    def _perform_eject(self, target, **kwargs):
        self._setup_eject_confirmation(target)
        self.log.debug("Ejecting ball to %s", target.name)

        if self.config['ball_switches']:
            # wait until one of the active switches turns off
            for switch in self.config['ball_switches']:
                # only consider active switches
                if self.machine.switch_controller.is_active(switch.name,
                        ms=self.config['entrance_count_delay']):
                    self.machine.switch_controller.add_switch_handler(
                        switch_name=switch.name,
                        callback=self._ball_left_device,
                        callback_kwargs={'balls': self.num_balls_ejecting},
                        state=0)

        if self.config['eject_coil']:
            if self.mechanical_eject_in_progress:
                self.log.debug("Will not fire eject coil because of mechanical eject")
            else:
                self._fire_eject_coil()

        elif self.config['hold_coil']:
            # TODO: wait for some time to allow balls to settle for
            #       both entrance and after a release

            self._disable_hold_coil()
            self.hold_release_in_progress = True

            # allow timed release of single balls and reenable coil after
            # release. Disable coil when device is empty
            self.delay.add(name='hold_coil_release',
                           ms=self.config['hold_coil_release_time'],
                           callback=self._hold_release_done)

        if not self.config['ball_switches']:
            # no ball_switches. we dont know when it actually leaves the device
            # assume its instant
            self.balls -= self.num_balls_ejecting
            return self._switch_state("ball_left")

    def _hold_release_done(self):
        self.hold_release_in_progress = False

        # reenable hold coil if there are balls left
        if self.balls > 0:
            self._enable_hold_coil()

    def _disable_hold_coil(self):
        self.config['hold_coil'].disable()
        if self.debug:
            self.log.debug("Disabling hold coil. num_balls_ejecting: %s. New "
                           "balls: %s.", self.num_balls_ejecting, self.balls)

    def hold(self, **kwargs):
        # do not enable coil when we are ejecting
        if self.hold_release_in_progress:
            return

        self._enable_hold_coil()

    def _enable_hold_coil(self):
        self.config['hold_coil'].enable()
        if self.debug:
            self.log.debug("Enabling hold coil. num_balls_ejecting: %s. New "
                           "balls: %s.", self.num_balls_ejecting, self.balls)

    def _fire_eject_coil(self):
        self.config['eject_coil'].pulse()
        if self.debug:
            self.log.debug("Firing eject coil. num_balls_ejecting: %s. New "
                           "balls: %s.", self.num_balls_ejecting, self.balls)

    def _setup_eject_confirmation(self, target):
        # Called after an eject request to confirm the eject. The exact method
        # of confirmation depends on how this ball device has been configured
        # and what target it's ejecting to

        # args are target device

        if self.debug:
            self.log.debug("Setting up eject confirmation")
            self.eject_start_time = time.time()
            self.log.debug("Eject start time: %s", self.eject_start_time)
            self.machine.events.add_handler('timer_tick', self._eject_status)


        timeout = self.config['eject_timeouts'][target]
        if timeout:
            # set up the delay to check for the failed the eject
            self.delay.add(name='target_eject_confirmation_timeout',
                           ms=timeout,
                           callback=self._eject_timeout)


        if self.config['confirm_eject_type'] == 'target':

            if not target:
                raise AssertionError("we got an eject confirmation request with no "
                                "target. This shouldn't happen. Post to the "
                                "forum if you see this.")


            if target.is_playfield():

                if target.ok_to_confirm_ball_via_playfield_switch():
                    if self.debug:
                        self.log.debug("Will confirm eject when a %s switch is "
                                       "hit", target.name)
                    self.machine.events.add_handler(
                        'sw_{}_active'.format(target.name), self._eject_success)
                else:
                    if self.debug:
                        self.log.debug("Will confirm eject via recount of ball "
                                       "switches.")
                    self._setup_count_eject_confirmation(timeout)



            if self.debug:
                self.log.debug("Will confirm eject via ball entry into '%s' "
                               "with a confirmation timeout of %sms",
                               target.name, timeout)

            # watch for ball entry event on the target device
            # Note this must be higher priority than the failed eject handler
            self.machine.events.add_handler(
                'balldevice_' + target.name +
                '_ball_enter', self._eject_success, priority=100000)

        elif self.config['confirm_eject_type'] == 'switch':
            if self.debug:
                self.log.debug("Will confirm eject via activation of switch "
                               "'%s'",
                               self.config['confirm_eject_switch'].name)
            # watch for that switch to activate momentarily
            # todo add support for a timed switch here
            self.machine.switch_controller.add_switch_handler(
                switch_name=self.config['confirm_eject_switch'].name,
                callback=self._eject_success,
                state=1, ms=0)

        elif self.config['confirm_eject_type'] == 'event':
            if self.debug:
                self.log.debug("Will confirm eject via posting of event '%s'",
                           self.config['confirm_eject_event'])
            # watch for that event
            self.machine.events.add_handler(
                self.config['confirm_eject_event'], self._eject_success)

        elif self.config['confirm_eject_type'] == 'count':
            # todo I think we need to set a delay to recount? Because if the
            # ball re-enters in less time than the exit delay, then the switch
            # handler won't have time to reregister it.
            if self.debug:
                self.log.debug("Will confirm eject via recount of ball "
                               "switches.")
            self._setup_count_eject_confirmation(timeout)

        elif self.config['confirm_eject_type'] == 'fake':
            # for all ball locks or captive balls which just release a ball
            # we use delay to keep the call order
            if self.config['ball_switches']:
                raise AssertionError("Cannot use fake with ball switches")

            self.delay.add(name='target_eject_confirmation_timeout',
                           ms=1, callback=self._eject_success)

        else:
            raise AssertionError("Invalid confirm_eject_type setting: " +
                            self.config['confirm_eject_type'])

    def _setup_count_eject_confirmation(self, timeout):
        if self._state == "waiting_for_ball_mechanical":
            # ball did not enter. if it does not enter
            self.delay.add(name='count_confirmation',
                            ms=timeout,
                            callback=self._eject_success)

        else:
            # wait until one of the active switches turns off
            for switch in self.config['ball_switches']:
                # only consider active switches
                if self.machine.switch_controller.is_active(switch.name,
                        ms=self.config['entrance_count_delay']):
                    self.machine.switch_controller.add_switch_handler(
                        switch_name=switch.name,
                        ms=self.config['exit_count_delay'],
                        callback=self._eject_success,
                        state=0)


    def _cancel_eject_confirmation(self):
        if self.debug:
            self.log.debug("Canceling eject confirmations")
        self.eject_in_progress_target = None
        self.num_eject_attempts = 0

        # Remove any event watching for success
        self.machine.events.remove_handler(self._eject_success)

        self.machine.events.remove_handlers_by_keys(
            self.pending_eject_event_keys)

        self.pending_eject_event_keys = set()

        self.waiting_for_eject_trigger = False
        self.mechanical_eject_in_progress = False

        # remove handler for ball left device
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self._ball_left_device,
                state=0)
            self.machine.switch_controller.remove_switch_handler(
                switch_name=switch.name,
                callback=self._eject_success,
                ms=self.config['exit_count_delay'],
                state=0)


        # Remove any switch handlers
        if self.config['confirm_eject_type'] == 'switch':
            self.machine.switch_controller.remove_switch_handler(
                switch_name=self.config['confirm_eject_switch'].name,
                callback=self._eject_success,
                state=1, ms=0)

        # Remove any delays that were watching for failures
        self.delay.remove('target_eject_confirmation_timeout')
        self.delay.remove('ball_missing_timeout')
        if self.config['mechanical_eject']:
            self.delay.remove('count_confirmation')

    def _inform_target_about_incoming_ball(self, target):
        target.add_incoming_ball(self)

    def _cancel_incoming_ball_at_target(self, target):
        target.remove_incoming_ball(self)

    def _eject_success(self, **kwargs):
        # We got an eject success for this device.
        # **kwargs because there are many ways to get here, some with kwargs
        # and some without. Also, since there are many ways we can get here,
        # let's first make sure we actually had an eject in progress


        if self._state == "ejecting":
            self.log.debug("Got an eject_success before the switch left the "
                           "device. Ignoring!")
            return

        if self.config['confirm_eject_type'] != 'target':
            self._inform_target_about_incoming_ball(self.eject_in_progress_target)


        if self._state == "waiting_for_ball_mechanical":
            # confirm eject of our source device
            self._incoming_balls[0][1]._eject_success()
            # remove eject from queue
            self.eject_queue.popleft()
            self._incoming_balls.popleft()
        elif self._state != "ball_left" and self._state != "failed_confirm":
            self.log.debug("Got an eject_success in wrong state %s!",
                    self._state)
            raise AssertionError("Invalid state " + self._state + " for _eject_success")


        if self.debug:
            self.log.debug("In _eject_success. Eject target: %s",
                           self.eject_in_progress_target)

        if self.debug:
            self.log.debug("Eject duration: %ss",
                           time.time() - self.eject_start_time)
            self.machine.events.remove_handler(self._eject_status)

        if self.debug:
            self.log.debug("Confirmed successful eject")

        # Create a temp attribute here so the real one is None when the
        # event is posted.
        eject_target = self.eject_in_progress_target
        self.num_jam_switch_count = 0
        self.num_eject_attempts = 0
        self.eject_in_progress_target = None
        balls_ejected = self.num_balls_ejecting
        self.num_balls_ejecting = 0

        # todo cancel post eject check delay
        self._cancel_eject_confirmation()

        self.machine.events.post('balldevice_' + self.name +
                                 '_ball_eject_success',
                                 balls=balls_ejected,
                                 target=eject_target)

        return self._switch_state("eject_confirmed")


    def _eject_timeout(self):
        if self.debug:
            self.log.debug("Got eject timeout")

        if self._state == "ball_left":
            return self._switch_state("failed_confirm")
        elif self._state == "ejecting":
            if not self.mechanical_eject_in_progress:
                self.eject_failed()
                return self._switch_state("failed_eject")
        elif self._state == "waiting_for_ball_mechanical":
            return
        else:
            raise AssertionError("Invalid state " + self._state)


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
        # Put the current target back in the queue so we can try again
        # This sets up the timeout back to the default. Wonder if we should
        # add some intelligence to make this longer or shorter?

        if self.debug:
            self.log.debug("Eject failed")

        if retry:
            self.eject_queue.appendleft((self.eject_in_progress_target, self.mechanical_eject_in_progress, self.trigger_event))

        # Remember variables for event
        target = self.eject_in_progress_target
        balls = self.num_balls_ejecting

        # Reset the stuff that showed a current eject in progress
        self.eject_in_progress_target = None
        self.num_balls_ejecting = 0
        self.num_eject_attempts += 1

        if self.debug:
            self.log.debug("Eject duration: %ss",
                          time.time() - self.eject_start_time)

        # cancel eject confirmations
        self._cancel_eject_confirmation()

        self.machine.events.post('balldevice_' + self.name +
                                 '_ball_eject_failed',
                                 target=target,
                                 balls=balls,
                                 retry=retry,
                                 num_attempts=self.num_eject_attempts)

    def _eject_permanently_failed(self):
        self.log.warning("Eject failed %s times. Permanently giving up.",
                         self.config['max_eject_attempts'])
        self.machine.events.post('balldevice_' + self.name +
                                 'ball_eject_permanent_failure')

    def _ok_to_receive(self):
        # Post an event announcing that it's ok for this device to receive a
        # ball
        self.machine.events.post(
            'balldevice_{}_ok_to_receive'.format(self.name),
            balls=self.get_additional_ball_capacity())

    def is_playfield(self):
        """Returns True if this ball device is a Playfield-type device, False
        if it's a regular ball device.

        """
        return False


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
