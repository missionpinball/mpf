"""Contains the base class for ball devices."""

from collections import deque

import asyncio

from mpf.devices.ball_device.ball_count_handler import BallCountHandler

from mpf.devices.ball_device.entrance_switch_counter import EntranceSwitchCounter
from mpf.devices.ball_device.hold_coil_ejector import HoldCoilEjector

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


from mpf.devices.ball_device.incoming_balls_handler import IncomingBallsHandler, IncomingBall
from mpf.devices.ball_device.outgoing_balls_handler import OutgoingBallsHandler, OutgoingBall
from mpf.devices.ball_device.pulse_coil_ejector import PulseCoilEjector
from mpf.devices.ball_device.switch_counter import SwitchCounter


@DeviceMonitor("available_balls", _state="state", counted_balls="balls")
class BallDevice(SystemWideDevice):

    """
    Base class for a 'Ball Device' in a pinball machine.

    A ball device is anything that can hold one or more balls, such as a
    trough, an eject hole, a VUK, a catapult, etc.

    Args: Same as Device.
    """

    config_section = 'ball_devices'
    collection = 'ball_devices'
    class_label = 'ball_device'

    def __init__(self, machine, name):
        """Initialise ball device."""
        super().__init__(machine, name)

        self.delay = DelayManager(machine.delayRegistry)

        self.available_balls = 0
        """Number of balls that are available to be ejected. This differs from
        `balls` since it's possible that this device could have balls that are
        being used for some other eject, and thus not available."""

        self._target_on_unexpected_ball = None
        # Device will eject to this target when it captures an unexpected ball

        self._source_devices = list()
        # Ball devices that have this device listed among their eject targets

        self._ball_requests = deque()
        # deque of tuples that holds requests from target devices for balls
        # that this device could fulfil
        # each tuple is (target device, boolean player_controlled flag)

        self.ejector = None
        self.counter = None
        self.ball_count_handler = None
        self.incoming_balls_handler = None
        self.outgoing_balls_handler = None

        # mirrored from ball_count_handler to make it obserable by the monitor
        self.counted_balls = 0
        self._state = "idle"

    def set_eject_state(self, state):
        """Set the current device state."""
        self._state = state

    @property
    def balls(self):
        """Return the number of balls we expect in the near future."""
        if self._state in ["ball_left", "failed_confirm"]:
            return self.counted_balls - 1
        return self.counted_balls

    def entrance(self, **kwargs):
        """Event handler for entrance events."""
        del kwargs
        self.counter.received_entrance_event()

    def _initialize(self):
        """Initialize right away."""
        super()._initialize()
        self._configure_targets()

        self.ball_count_handler = BallCountHandler(self)
        self.incoming_balls_handler = IncomingBallsHandler(self)
        self.outgoing_balls_handler = OutgoingBallsHandler(self)

        # delay ball counters because we have to wait for switches to be ready
        self.machine.events.add_handler('init_phase_2', self._create_ball_counters)

        # check to make sure no switches from this device are tagged with
        # playfield_active, because ball devices have their own logic for
        # working with the playfield and this will break things. Plus, a ball
        # in a ball device is not technically on the playfield.

        switch_set = set()

        for section in ('hold_switches', 'ball_switches'):
            for switch in self.config[section]:
                switch_set.add(switch)

        if self.config['entrance_switch']:
            switch_set.add(self.config['jam_switch'])

        if self.config['entrance_switch']:
            switch_set.add(self.config['jam_switch'])

        for switch in switch_set:
            if switch and 'playfield_active' in switch.tags:
                raise ValueError(
                    "Ball device '{}' uses switch '{}' which has a "
                    "'playfield_active' tag. This is not valid. Remove the "
                    "'playfield_active' tag from that switch.".format(
                        self.name, switch.name))

    def _create_ball_counters(self, **kwargs):
        del kwargs
        if self.config['ball_switches']:
            self.counter = SwitchCounter(self, self.config)     # pylint: disable-msg=redefined-variable-type
        else:
            self.counter = EntranceSwitchCounter(self, self.config)  # pylint: disable-msg=redefined-variable-type

        self.machine.clock.loop.run_until_complete(self._initialize_async())

    def stop_device(self):
        """Stop device."""
        self.ball_count_handler.stop()
        self.incoming_balls_handler.stop()
        self.outgoing_balls_handler.stop()
        self.debug_log("Stopping ball device")

    @asyncio.coroutine
    def expected_ball_received(self):
        """Handle an expected ball."""
        # post enter event
        yield from self._post_enter_event(unclaimed_balls=0)

    @asyncio.coroutine
    def unexpected_ball_received(self):
        """Handle an unexpected ball."""
        # capture from playfield
        yield from self._post_capture_from_playfield_event()
        # post enter event
        unclaimed_balls = yield from self._post_enter_event(unclaimed_balls=1)
        # add available_balls and route unclaimed ball to the default target
        self._balls_added_callback(1, unclaimed_balls)

    @asyncio.coroutine
    def lost_idle_ball(self):
        """Lost an ball while the device was idle."""
        if self.config['mechanical_eject']:
            # handle lost balls via outgoing balls handler (if mechanical eject)
            self.config['eject_targets'][0].available_balls += 1
            eject = OutgoingBall(self.config['eject_targets'][0])
            eject.eject_timeout = self.config['eject_timeouts'][eject.target] / 1000
            eject.max_tries = self.config['max_eject_attempts']
            eject.mechanical = True
            eject.already_left = True
            self.outgoing_balls_handler.add_eject_to_queue(eject)
        else:
            # handle lost balls
            self.config['ball_missing_target'].add_missing_balls(1)
            yield from self._balls_missing(1)

    @asyncio.coroutine
    def lost_ejected_ball(self, target):
        """Handle an outgoing lost ball."""
        # follow path and check if we should request a new ball to the target or cancel the path
        if target.is_playfield():
            raise AssertionError("Lost a ball to playfield {}. This should not happen".format(target))
        elif target.cancel_path_if_target_is(self, self.config['ball_missing_target']):
            # add ball to default target because it would have gone there anyway
            self.warning_log("Path to %s canceled. Assuming the ball jumped to %s.", target,
                             self.config['ball_missing_target'])
        elif target.find_available_ball_in_path(self):
            self.warning_log("Path is not going to ball_missing_target %s. Restoring path by requesting new ball to "
                             "target %s.", self.config['ball_missing_target'], target)
            # remove one ball first because it will get a new one with the eject
            target.available_balls -= 1
            self.eject(target=target)
        else:
            self.warning_log("Failed to restore the path. If you can reproduce this please report in the forum!")

        self.config['ball_missing_target'].add_missing_balls(1)
        yield from self._balls_missing(1)

    @asyncio.coroutine
    def lost_incoming_ball(self, source):
        """Handle lost ball which was confirmed to have left source."""
        del source
        if self.cancel_path_if_target_is(self, self.config['ball_missing_target']):
            # add ball to default target
            self.warning_log("Path to canceled. Assuming the ball jumped to %s.", self.config['ball_missing_target'])
        elif self.find_available_ball_in_path(self):
            self.warning_log("Path is not going to ball_missing_target %s. Restoring path by requesting a new ball.",
                             self.config['ball_missing_target'])
            self.available_balls -= 1
            self.request_ball()
        else:
            self.warning_log("Failed to restore the path. If you can reproduce this please report in the forum!")

        self.config['ball_missing_target'].add_missing_balls(1)
        yield from self._balls_missing(1)

    def cancel_path_if_target_is(self, start, target):
        """Check if the ball is going to a certain target and cancel the path in that case."""
        return self.outgoing_balls_handler.cancel_path_if_target_is(start, target)

    def find_available_ball_in_path(self, start):
        """Try to remove available ball at the end of the path."""
        return self.outgoing_balls_handler.find_available_ball_in_path(start)

    @asyncio.coroutine
    def _initialize_async(self):
        """Count balls without handling them as new."""
        yield from self.ball_count_handler.initialise()
        yield from self.incoming_balls_handler.initialise()
        yield from self.outgoing_balls_handler.initialise()

        self.available_balls = self.ball_count_handler.handled_balls

    @asyncio.coroutine
    def _post_capture_from_playfield_event(self):
        yield from self.machine.events.post_async('balldevice_captured_from_{}'.format(
            self.config['captures_from'].name),
            balls=1)
        '''event: balldevice_captured_from_(device)

        desc: A ball device has just captured a ball from the device called
        (device)

        args:
        balls: The number of balls that were captured.

        '''

    @asyncio.coroutine
    def _post_enter_event(self, unclaimed_balls):
        self.debug_log("Processing new ball")
        result = yield from self.machine.events.post_relay_async('balldevice_{}_ball_enter'.format(
            self.name),
            new_balls=1,
            unclaimed_balls=unclaimed_balls,
            device=self)
        '''event: balldevice_(name)_ball_enter

        desc: A ball (or balls) have just entered the ball device called
        "name".

        Note that this is a relay event based on the "unclaimed_balls" arg. Any
        unclaimed balls in the relay will be processed as new balls entering
        this device.

        args:

        unclaimed_balls: The number of balls that have not yet been claimed.
        device: A reference to the ball device object that is posting this
        event.
        '''
        return result['unclaimed_balls']

    def add_incoming_ball(self, incoming_ball: IncomingBall):
        """Notify this device that there is a ball heading its way."""
        self.incoming_balls_handler.add_incoming_ball(incoming_ball)

    def remove_incoming_ball(self, incoming_ball: IncomingBall):
        """Remove a ball from the incoming balls queue."""
        self.incoming_balls_handler.remove_incoming_ball(incoming_ball)

    def wait_for_ready_to_receive(self, source):
        """Wait until this device is ready to receive a ball."""
        return self.ball_count_handler.wait_for_ready_to_receive(source)

    def _source_device_balls_available(self, **kwargs):
        del kwargs
        if len(self._ball_requests):
            (target, player_controlled) = self._ball_requests.popleft()
            if self._setup_or_queue_eject_to_target(target, player_controlled):
                return False

    # ---------------------- End of state handling code -----------------------

    def _parse_config(self):
        # ensure eject timeouts list matches the length of the eject targets
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
                Util.string_to_ms(timeouts_list[i]))

        timeouts_list = self.config['ball_missing_timeouts']
        self.config['ball_missing_timeouts'] = dict()

        for i in range(len(self.config['eject_targets'])):
            self.config['ball_missing_timeouts'][
                self.config['eject_targets'][i]] = (
                Util.string_to_ms(timeouts_list[i]))
        # End code to create timeouts list ------------------------------------

        # cannot have ball switches and capacity
        if self.config['ball_switches'] and self.config['ball_capacity']:
            raise AssertionError("Cannot use capacity and ball switches.")
        elif not self.config['ball_capacity'] and not self.config['ball_switches']:
            raise AssertionError("Need ball capcity if there are no switches.")
        elif self.config['ball_switches']:
            self.config['ball_capacity'] = len(self.config['ball_switches'])

    @property
    def capacity(self):
        """Return the ball capacity."""
        return self.config['ball_capacity']

    def _validate_config(self):
        # perform logical validation
        # a device cannot have hold_coil and eject_coil
        if (not self.config['eject_coil'] and not self.config['hold_coil'] and
                not self.config['mechanical_eject']):
            raise AssertionError('Configuration error in {} ball device. '
                                 'Device needs an eject_coil, a hold_coil, or '
                                 '"mechanical_eject: True"'.format(self.name))

        # entrance switch + mechanical eject is not supported
        if (len(self.config['ball_switches']) > 1 and
                self.config['mechanical_eject']):
            raise AssertionError('Configuration error in {} ball device. '
                                 'mechanical_eject can only be used with '
                                 'devices that have 1 ball switch'.
                                 format(self.name))

        # make sure timeouts are reasonable:
        # exit_count_delay < all eject_timeout
        if self.config['exit_count_delay'] > min(
                self.config['eject_timeouts'].values()):
            raise AssertionError('Configuration error in {} ball device. '
                                 'all eject_timeouts have to be larger than '
                                 'exit_count_delay'.
                                 format(self.name))

        # entrance_count_delay < all eject_timeout
        if self.config['entrance_count_delay'] > min(
                self.config['eject_timeouts'].values()):
            raise AssertionError('Configuration error in {} ball device. '
                                 'all eject_timeouts have to be larger than '
                                 'entrance_count_delay'.
                                 format(self.name))

        # all eject_timeout < all ball_missing_timeouts
        if max(self.config['eject_timeouts'].values()) > min(
                self.config['ball_missing_timeouts'].values()):
            raise AssertionError('Configuration error in {} ball device. '
                                 'all ball_missing_timeouts have to be larger '
                                 'than all eject_timeouts'.
                                 format(self.name))

        # all ball_missing_timeouts < incoming ball timeout
        if max(self.config['ball_missing_timeouts'].values()) > 60000:
            raise AssertionError('Configuration error in {} ball device. '
                                 'incoming ball timeout has to be larger '
                                 'than all ball_missing_timeouts'.
                                 format(self.name))

        if (self.config['confirm_eject_type'] == "switch" and
                not self.config['confirm_eject_switch']):
            raise AssertionError("When using confirm_eject_type switch you " +
                                 "to specify a confirm_eject_switch")

        if "drain" in self.tags and "trough" not in self.tags and not self.find_next_trough():
            raise AssertionError("No path to trough but device is tagged as drain")

        if ("drain" not in self.tags and "trough" not in self.tags and
                not self.find_path_to_target(self._target_on_unexpected_ball)):
            raise AssertionError("BallDevice {} has no path to target_on_unexpected_ball '{}'".format(
                self.name, self._target_on_unexpected_ball.name))

    def load_config(self, config):
        """Load config."""
        super().load_config(config)

        # load targets and timeouts
        self._parse_config()

    def _configure_targets(self):
        if self.config['target_on_unexpected_ball']:
            self._target_on_unexpected_ball = self.config['target_on_unexpected_ball']
        else:
            self._target_on_unexpected_ball = self.config['captures_from']

        # validate that configuration is valid
        self._validate_config()

        if self.config['eject_coil']:
            self.ejector = PulseCoilEjector(self)   # pylint: disable-msg=redefined-variable-type
        elif self.config['hold_coil']:
            self.ejector = HoldCoilEjector(self)    # pylint: disable-msg=redefined-variable-type

        if self.ejector and self.config['ball_search_order']:
            self.config['captures_from'].ball_search.register(
                self.config['ball_search_order'], self.ejector.ball_search,
                self.name)

        # Register events to watch for ejects targeted at this device
        for device in self.machine.ball_devices:
            if device.is_playfield():
                continue
            for target in device.config['eject_targets']:
                if target.name == self.name:
                    self._source_devices.append(device)
                    self.debug_log("EVENT: %s to %s", device.name, target.name)

                    self.machine.events.add_handler(
                        'balldevice_balls_available',
                        self._source_device_balls_available)

                    break

    def _balls_added_callback(self, new_balls, unclaimed_balls):
        # If we still have unclaimed_balls here, that means that no one claimed
        # them, so essentially they're "stuck." So we just eject them unless
        # this device is tagged 'trough' in which case we let it keep them.
        self.debug_log("Adding ball")
        self.available_balls += new_balls

        if unclaimed_balls:
            if 'trough' in self.tags:
                # ball already reached trough. everything is fine
                pass
            elif 'drain' in self.tags:
                # try to eject to next trough
                trough = self.find_next_trough()

                if not trough:
                    raise AssertionError("Could not find path to trough")

                for dummy_iterator in range(unclaimed_balls):
                    self._setup_or_queue_eject_to_target(trough)
            else:
                target = self._target_on_unexpected_ball

                # try to eject to configured target
                path = self.find_path_to_target(target)

                if not path:
                    raise AssertionError("Could not find path to playfield {}".format(target.name))

                self.debug_log("Ejecting %s unexpected balls using path %s", unclaimed_balls, path)

                for dummy_iterator in range(unclaimed_balls):
                    self.setup_eject_chain(path, not self.config['auto_fire_on_unexpected_ball'])

        # we might have ball requests locally. serve them first
        if self._ball_requests:
            self._source_device_balls_available()

        # tell targets that we have balls available
        for dummy_iterator in range(new_balls):
            self.machine.events.post_boolean('balldevice_balls_available')

    @asyncio.coroutine
    def _balls_missing(self, balls):
        # Called when ball_count finds that balls are missing from this device
        self.debug_log("%s ball(s) missing from device. Mechanical eject?"
                       " %s", abs(balls), self.config['mechanical_eject'])

        yield from self.machine.events.post_async('balldevice_{}_ball_missing'.format(abs(balls)))
        '''event: balldevice_(balls)_ball_missing.
        desc: The number of (balls) is missing. Note this event is
        posted in addition to the generic *balldevice_ball_missing* event.
        '''
        yield from self.machine.events.post_async('balldevice_ball_missing', balls=abs(balls))
        '''event: balldevice_ball_missing
        desc: A ball is missing from a device.
        args:
            balls: The number of balls that are missing
        '''

    @property
    def state(self):
        """Return the device state."""
        return self._state

    def find_one_available_ball(self, path=deque()):
        """Find a path to a source device which has at least one available ball."""
        # copy path
        path = deque(path)

        # prevent loops
        if self in path:
            return False

        path.appendleft(self)

        if self.available_balls > 0 and len(path) > 1:
            return path

        for source in self._source_devices:
            full_path = source.find_one_available_ball(path=path)
            if full_path:
                return full_path

        return False

    def request_ball(self, balls=1, **kwargs):
        """Request that one or more balls is added to this device.

        Args:
            balls: Integer of the number of balls that should be added to this
                device. A value of -1 will cause this device to try to fill
                itself.
            **kwargs: unused
        """
        del kwargs
        self.debug_log("Requesting Ball(s). Balls=%s", balls)

        for dummy_iterator in range(balls):
            self._setup_or_queue_eject_to_target(self)

        return balls

    def _setup_or_queue_eject_to_target(self, target, player_controlled=False):
        path_to_target = self.find_path_to_target(target)
        if self.available_balls > 0 and self != target:
            path = path_to_target
        else:

            path = self.find_one_available_ball()
            if not path:
                # put into queue here
                self._ball_requests.append((target, player_controlled))
                return False

            if target != self:
                if target not in self.config['eject_targets']:
                    raise AssertionError(
                        "Do not know how to eject to " + target.name)

                path_to_target.popleft()    # remove self from path
                path.extend(path_to_target)

        path[0].setup_eject_chain(path, player_controlled)

        return True

    def setup_player_controlled_eject(self, target=None):
        """Setup a player controlled eject."""
        self.debug_log("Setting up player-controlled eject. Balls: %s, "
                       "Target: %s, player_controlled_eject_event: %s",
                       1, target,
                       self.config['player_controlled_eject_event'])

        if self.config['mechanical_eject'] or (
                self.config['player_controlled_eject_event'] and self.ejector):

            self._setup_or_queue_eject_to_target(target, True)

        else:
            self.eject(target=target)

    def setup_eject_chain(self, path, player_controlled=False):
        """Setup an eject chain."""
        path = deque(path)
        if self.available_balls <= 0:
            raise AssertionError("Tried to setup an eject chain, but there are"
                                 " no available balls. Device: {}, Path: {}"
                                 .format(self.name, path))

        self.available_balls -= 1

        target = path[len(path) - 1]
        source = path.popleft()
        if source != self:
            raise AssertionError("Path starts somewhere else!")

        self.setup_eject_chain_next_hop(path, player_controlled)

        target.available_balls += 1

        self.machine.events.post_boolean('balldevice_balls_available')
        '''event: balldevice_balls_available
        desc: A device has balls available to be ejected.
        '''

    def setup_eject_chain_next_hop(self, path, player_controlled):
        """Setup one hop of the eject chain."""
        next_hop = path.popleft()
        self.debug_log("Adding eject chain")

        if next_hop not in self.config['eject_targets']:
            raise AssertionError("Broken path")

        eject = OutgoingBall(next_hop)
        eject.eject_timeout = self.config['eject_timeouts'][next_hop] / 1000
        eject.max_tries = self.config['max_eject_attempts']
        eject.mechanical = player_controlled

        self.outgoing_balls_handler.add_eject_to_queue(eject)

        # check if we traversed the whole path
        if len(path) > 0:
            next_hop.setup_eject_chain_next_hop(path, player_controlled)

    def find_next_trough(self):
        """Find next trough after device."""
        # are we a trough?
        if 'trough' in self.tags:
            return self

        # otherwise find any target which can
        for target_device in self.config['eject_targets']:
            if target_device.is_playfield():
                continue
            trough = target_device.find_next_trough()
            if trough:
                return trough

        return False

    def find_path_to_target(self, target):
        """Find a path to this target."""
        # if we can eject to target directly just do it
        if target in self.config['eject_targets']:
            path = deque()
            path.appendleft(target)
            path.appendleft(self)
            return path
        else:
            # otherwise find any target which can
            for target_device in self.config['eject_targets']:
                if target_device.is_playfield():
                    continue
                path = target_device.find_path_to_target(target)
                if path:
                    path.appendleft(self)
                    return path

        return False

    def eject(self, balls=1, target=None, **kwargs):
        """Eject ball to target."""
        del kwargs
        if not target:
            target = self._target_on_unexpected_ball

        self.debug_log('Adding %s ball(s) to the eject_queue with target %s.',
                       balls, target)

        # add request to queue
        for dummy_iterator in range(balls):
            self._setup_or_queue_eject_to_target(target)

    def eject_all(self, target=None, **kwargs):
        """Eject all the balls from this device.

        Args:
            target: The string or BallDevice target for this eject. Default of
                None means `playfield`.
            **kwargs: unused

        Returns:
            True if there are balls to eject. False if this device is empty.
        """
        del kwargs
        self.debug_log("Ejecting all balls")
        if self.available_balls > 0:
            self.eject(balls=self.available_balls, target=target)
            return True
        else:
            return False

    def hold(self, **kwargs):
        """Event handler for hold event."""
        del kwargs
        # TODO: remove when migrating config to ejectors
        self.ejector.hold()

    @classmethod
    def is_playfield(cls):
        """Return True if this ball device is a Playfield-type device, False if it's a regular ball device."""
        return False
