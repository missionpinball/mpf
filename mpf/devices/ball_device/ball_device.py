"""Contains the base class for ball devices."""
import asyncio
from collections import deque

from mpf.core.events import QueuedEvent, event_handler
from mpf.devices.ball_device.ball_count_handler import BallCountHandler
from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice
from mpf.core.utility_functions import Util


from mpf.devices.ball_device.incoming_balls_handler import IncomingBallsHandler, IncomingBall
from mpf.devices.ball_device.outgoing_balls_handler import OutgoingBallsHandler, OutgoingBall


@DeviceMonitor("available_balls", _state="state", counted_balls="balls")
class BallDevice(SystemWideDevice):

    """Base class for a 'Ball Device' in a pinball machine.

    A ball device is anything that can hold one or more balls, such as a
    trough, an eject hole, a VUK, a catapult, etc.

    Args: Same as Device.
    """

    config_section = 'ball_devices'
    collection = 'ball_devices'
    class_label = 'ball_device'

    __slots__ = ["delay", "available_balls", "_target_on_unexpected_ball", "_source_devices", "_ball_requests",
                 "ejector", "ball_count_handler", "incoming_balls_handler", "outgoing_balls_handler",
                 "counted_balls", "_state"]

    def __init__(self, machine, name):
        """Initialise ball device."""
        super().__init__(machine, name)

        self.delay = DelayManager(machine)

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

        self.ejector = None                     # type: BallDeviceEjector
        self.ball_count_handler = None          # type: BallCountHandler
        self.incoming_balls_handler = None      # type: IncomingBallsHandler
        self.outgoing_balls_handler = None      # type: OutgoingBallsHandler

        # mirrored from ball_count_handler to make it obserable by the monitor
        self.counted_balls = 0
        self._state = "idle"

    def set_eject_state(self, state):
        """Set the current device state."""
        self.info_log("State: %s", state)
        self._state = state

    @property
    def balls(self):
        """Return the number of balls we expect in the near future."""
        if self._state in ["ball_left", "failed_confirm"]:
            return self.counted_balls - 1
        return self.counted_balls

    @event_handler(11)
    def event_entrance(self, **kwargs):
        """Event handler for entrance events."""
        del kwargs
        self.ball_count_handler.counter.received_entrance_event()

    async def _initialize(self):
        """Initialize right away."""
        await super()._initialize()
        self._configure_targets()

        self.ball_count_handler = BallCountHandler(self)
        self.incoming_balls_handler = IncomingBallsHandler(self)
        self.outgoing_balls_handler = OutgoingBallsHandler(self)

        # delay ball counters because we have to wait for switches to be ready
        self.machine.events.add_handler('init_phase_2', self._initialize_late)

    def _initialize_late(self, queue: QueuedEvent, **kwargs):
        """Create ball counters."""
        del kwargs
        queue.wait()
        complete_future = asyncio.ensure_future(self._initialize_async())
        complete_future.add_done_callback(lambda x: queue.clear())

    def stop_device(self):
        """Stop device."""
        self.debug_log("Stopping ball device")
        if self.ball_count_handler:
            self.ball_count_handler.stop()
            self.incoming_balls_handler.stop()
            self.outgoing_balls_handler.stop()

    async def expected_ball_received(self):
        """Handle an expected ball."""
        # post enter event
        unclaimed_balls = await self._post_enter_event(unclaimed_balls=0, new_available_balls=0)
        # there might still be unclaimed balls (e.g. because of a ball_routing)
        self._balls_added_callback(0, unclaimed_balls)

    async def unexpected_ball_received(self):
        """Handle an unexpected ball."""
        # capture from playfield
        await self._post_capture_from_playfield_event()
        # post enter event
        unclaimed_balls = await self._post_enter_event(unclaimed_balls=1, new_available_balls=1)
        # add available_balls and route unclaimed ball to the default target
        self._balls_added_callback(1, unclaimed_balls)

    async def handle_mechanial_eject_during_idle(self):
        """Handle mechanical eject."""
        # handle lost balls via outgoing balls handler (if mechanical eject)
        self.config['eject_targets'][0].available_balls += 1
        eject = OutgoingBall(self.config['eject_targets'][0])
        eject.eject_timeout = self.config['eject_timeouts'][eject.target] / 1000
        eject.max_tries = self.config['max_eject_attempts']
        eject.player_controlled = True
        eject.already_left = True
        self.outgoing_balls_handler.add_eject_to_queue(eject)

    async def lost_idle_ball(self):
        """Lost an ball while the device was idle."""
        # handle lost balls
        self.warning_log("Ball disappeared while idle. This should not normally happen.")
        self.available_balls -= 1
        self.config['ball_missing_target'].add_missing_balls(1)
        await self._balls_missing(1)

    async def lost_ejected_ball(self, target):
        """Handle an outgoing lost ball."""
        # follow path and check if we should request a new ball to the target or cancel the path
        if target.is_playfield():
            raise AssertionError("Lost a ball to playfield {}. This should not happen".format(target))
        if target.cancel_path_if_target_is(self, self.config['ball_missing_target']):
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
        await self._balls_missing(1)

    async def lost_incoming_ball(self, source):
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
        await self._balls_missing(1)

    def cancel_path_if_target_is(self, start, target):
        """Check if the ball is going to a certain target and cancel the path in that case."""
        return self.outgoing_balls_handler.cancel_path_if_target_is(start, target)

    def find_available_ball_in_path(self, start):
        """Try to remove available ball at the end of the path."""
        return self.outgoing_balls_handler.find_available_ball_in_path(start)

    async def _initialize_async(self):
        """Count balls without handling them as new."""
        await self.ball_count_handler.initialise()
        await self.incoming_balls_handler.initialise()
        await self.outgoing_balls_handler.initialise()

        self.available_balls = self.ball_count_handler.handled_balls

    async def _post_capture_from_playfield_event(self):
        await self.machine.events.post_async('balldevice_captured_from_{}'.format(
            self.config['captures_from'].name),
            balls=1)
        '''event: balldevice_captured_from_(captures_from)

        desc: A ball device has just captured a ball from the device called
        (captures_from)

        args:
        balls: The number of balls that were captured.

        '''

    async def _post_enter_event(self, unclaimed_balls, new_available_balls):
        self.debug_log("Processing new ball")
        result = await self.machine.events.post_relay_async('balldevice_{}_ball_enter'.format(
            self.name),
            new_balls=1,
            unclaimed_balls=unclaimed_balls,
            new_available_balls=new_available_balls,
            device=self)
        '''event: balldevice_(name)_ball_enter

        desc: A ball (or balls) have just entered the ball device called
        "name".

        Note that this is a relay event based on the "unclaimed_balls" arg. Any
        unclaimed balls in the relay will be processed as new balls entering
        this device.

        Please be aware that we did not add those balls to balls or available_balls of the device during this event.

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

    @property
    def requested_balls(self):
        """Return the number of requested balls."""
        return len(self._ball_requests)

    def _source_device_balls_available(self, **kwargs) -> None:
        del kwargs
        if self._ball_requests:
            (target, player_controlled) = self._ball_requests.popleft()
            self._setup_or_queue_eject_to_target(target, player_controlled)

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

    @property
    def capacity(self):
        """Return the ball capacity."""
        return self.ball_count_handler.counter.capacity

    def _validate_config(self):
        # perform logical validation
        # a device cannot have hold_coil and eject_coil
        if (not self.config.get('eject_coil') and not self.config.get('hold_coil') and
                not self.config['mechanical_eject'] and not self.config.get('ejector', False)):
            self.raise_config_error('Configuration error in {} ball device. '
                                    'Device needs an eject_coil, a hold_coil, or '
                                    '"mechanical_eject: True"'.format(self.name), 4)

        # all eject_timeout < all ball_missing_timeouts
        if max(self.config['eject_timeouts'].values()) > min(
                self.config['ball_missing_timeouts'].values()):
            self.raise_config_error('Configuration error in {} ball device. '
                                    'all ball_missing_timeouts have to be larger '
                                    'than all eject_timeouts'.
                                    format(self.name), 8)

        # all ball_missing_timeouts < incoming ball timeout
        if max(self.config['ball_missing_timeouts'].values()) > 60000:
            self.raise_config_error('Configuration error in {} ball device. '
                                    'incoming ball timeout has to be larger '
                                    'than all ball_missing_timeouts'.
                                    format(self.name), 9)

        if (self.config['confirm_eject_type'] == "switch" and
                not self.config['confirm_eject_switch']):
            self.raise_config_error("When using confirm_eject_type switch you " +
                                    "to specify a confirm_eject_switch", 7)

        if (self.config['confirm_eject_type'] == "event" and
                not self.config['confirm_eject_event']):
            self.raise_config_error("When using confirm_eject_type event you " +
                                    "to specify a confirm_eject_event", 14)

        if "ball_add_live" in self.tags:
            self.raise_config_error("Using \"tag: ball_add_live\" is deprecated. Please use default_source_device "
                                    "in your playfield section instead.", 10)

        if "drain" in self.tags and "trough" not in self.tags and not self.find_next_trough():
            self.raise_config_error("No path to trough but device is tagged as drain", 11)

        if ("drain" not in self.tags and "trough" not in self.tags and
                not self.find_path_to_target(self._target_on_unexpected_ball)):
            self.raise_config_error("BallDevice {} has no path to target_on_unexpected_ball '{}'".format(
                self.name, self._target_on_unexpected_ball.name), 12)

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

        ejector_config = self.config.get("ejector", {})

        # no ejector config. support legacy config
        if not ejector_config:
            if self.config.get('eject_coil'):
                if self.config.get('eject_coil_enable_time'):
                    ejector_config["class"] = "mpf.devices.ball_device.enable_coil_ejector.EnableCoilEjector"
                else:
                    ejector_config["class"] = "mpf.devices.ball_device.pulse_coil_ejector.PulseCoilEjector"
            elif self.config.get('hold_coil'):
                ejector_config["class"] = "mpf.devices.ball_device.hold_coil_ejector.HoldCoilEjector"

        if not ejector_config:
            self.debug_log("Device does not have any ejector.")
        else:
            ejector_class = Util.string_to_class(ejector_config["class"])
            if not ejector_class:
                self.raise_config_error("Could not load ejector {}".format(ejector_config["class"]), 1)

            self.ejector = ejector_class(ejector_config, self, self.machine)

        if self.ejector and self.config['ball_search_order']:
            self.config['captures_from'].ball_search.register(
                self.config['ball_search_order'], self.ejector.ball_search,
                self.name)

        # Register events to watch for ejects targeted at this device
        for device in self.machine.ball_devices.values():
            if device.is_playfield():
                continue
            for target in device.config['eject_targets']:
                if target.name == self.name:
                    self._source_devices.append(device)
                    break

        # register event handler for available balls at source devices
        self.machine.events.add_handler(
            'balldevice_balls_available',
            self._source_device_balls_available)

    def _balls_added_callback(self, new_balls, unclaimed_balls):
        # If we still have unclaimed_balls here, that means that no one claimed
        # them, so essentially they're "stuck." So we just eject them unless
        # this device is tagged 'trough' in which case we let it keep them.
        self.debug_log("Adding ball")
        self.available_balls += new_balls

        if unclaimed_balls and self.available_balls > 0:
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

                self.info_log("Ejecting %s unexpected balls using path %s", unclaimed_balls, path)

                for dummy_iterator in range(unclaimed_balls):
                    self.setup_eject_chain(path, not self.config['auto_fire_on_unexpected_ball'])

        # we might have ball requests locally. serve them first
        if self._ball_requests:
            self._source_device_balls_available()

        # tell targets that we have balls available
        for dummy_iterator in range(new_balls):
            self.machine.events.post_boolean('balldevice_balls_available')

        self.machine.events.post('balldevice_{}_ball_entered'.format(self.name), new_balls=new_balls, device=self)
        '''event: balldevice_(name)_ball_entered

        desc: A ball (or balls) have just entered the ball device called
        "name".

        The ball was also added to balls and available_balls of the device.

        args:

        new_balls: The number of new balls that have not been claimed (by locks or similar).
        device: A reference to the ball device object that is posting this
        event.
        '''

    async def _balls_missing(self, balls):
        # Called when ball_count finds that balls are missing from this device
        self.info_log("%s ball(s) missing from device. Mechanical eject?"
                      " %s", abs(balls), self.config['mechanical_eject'])

        await self.machine.events.post_async('balldevice_{}_ball_missing'.format(self.name), balls=abs(balls))
        '''event: balldevice_(name)_ball_missing
        desc: The device (name) is missing a ball. Note this event is
        posted in addition to the generic *balldevice_ball_missing* event.
        args:
            balls: The number of balls that are missing
        '''
        await self.machine.events.post_async('balldevice_ball_missing', balls=abs(balls), name=self.name)
        '''event: balldevice_ball_missing
        desc: A ball is missing from a device.
        args:
            balls: The number of balls that are missing
            name: Name of device which lost the ball
        '''

    @property
    def state(self):
        """Return the device state."""
        return self._state

    def find_one_available_ball(self, path=None):
        """Find a path to a source device which has at least one available ball."""
        if path is None:
            path = deque()
        else:
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

    @event_handler(1)
    def event_request_ball(self, balls=1, **kwargs):
        """Handle request_ball control event."""
        del kwargs
        self.request_ball(balls)

    def request_ball(self, balls=1):
        """Request that one or more balls is added to this device.

        Args:
        ----
            balls: Integer of the number of balls that should be added to this
                device. A value of -1 will cause this device to try to fill
                itself.
            **kwargs: unused
        """
        self.debug_log("Requesting Ball(s). Balls=%s", balls)

        for dummy_iterator in range(balls):
            self._setup_or_queue_eject_to_target(self)

        return balls

    def _setup_or_queue_eject_to_target(self, target, player_controlled=False):
        path_to_target = self.find_path_to_target(target)
        if target != self and not path_to_target:
            raise AssertionError("Do not know how to eject to {}".format(target.name))

        if self.available_balls > 0 and self != target:
            path = path_to_target
        else:

            path = self.find_one_available_ball()
            if not path:
                # put into queue here
                self._ball_requests.append((target, player_controlled))
                return False

            if target != self:
                path_to_target.popleft()    # remove self from path
                path.extend(path_to_target)

        path[0].setup_eject_chain(path, player_controlled)

        return True

    def setup_player_controlled_eject(self, target=None):
        """Set up a player controlled eject."""
        self.info_log("Setting up player-controlled eject. Balls: %s, "
                      "Target: %s, player_controlled_eject_event: %s",
                      1, target,
                      self.config['player_controlled_eject_event'])

        if self.config['mechanical_eject'] or (
                self.config['player_controlled_eject_event'] and self.ejector):

            self._setup_or_queue_eject_to_target(target, True)

        else:
            self.eject(target=target)

    def setup_eject_chain(self, path, player_controlled=False):
        """Set up an eject chain."""
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
        """Set up one hop of the eject chain."""
        next_hop = path.popleft()
        self.debug_log("Adding eject chain")

        if next_hop not in self.config['eject_targets']:
            raise AssertionError("Broken path")

        eject = OutgoingBall(next_hop)
        eject.eject_timeout = self.config['eject_timeouts'][next_hop] / 1000
        eject.max_tries = self.config['max_eject_attempts']
        eject.player_controlled = player_controlled

        self.outgoing_balls_handler.add_eject_to_queue(eject)

        # check if we traversed the whole path
        if path:
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

        # otherwise find any target which can
        for target_device in self.config['eject_targets']:
            if target_device.is_playfield():
                continue
            path = target_device.find_path_to_target(target)
            if path:
                path.appendleft(self)
                return path

        return False

    @event_handler(2)
    def event_eject(self, balls=1, target=None, **kwargs):
        """Handle eject control event."""
        del kwargs
        self.eject(balls, target)

    def eject(self, balls=1, target=None) -> int:
        """Eject balls to target.

        Return the number of balls found for eject. The remaining balls are queued for eject when available.
        """
        if not target:
            target = self._target_on_unexpected_ball

        self.info_log('Adding %s ball(s) to the eject_queue with target %s.',
                      balls, target)

        balls_found = 0
        # add request to queue
        for dummy_iterator in range(balls):
            if self._setup_or_queue_eject_to_target(target):
                balls_found += 1

        return balls_found

    @event_handler(3)
    def event_eject_all(self, target=None, **kwargs):
        """Handle eject_all control event."""
        del kwargs
        self.eject_all(target)

    def eject_all(self, target=None) -> bool:
        """Eject all the balls from this device.

        Args:
        ----
            target: The string or BallDevice target for this eject. Default of
                None means `playfield`.
            **kwargs: unused

        Returns True if there are balls to eject. False if this device is empty.
        """
        self.debug_log("Ejecting all balls")
        if self.available_balls > 0:
            self.eject(balls=self.available_balls, target=target)
            return True

        return False

    @classmethod
    def is_playfield(cls):
        """Return True if this ball device is a Playfield-type device, False if it's a regular ball device."""
        return False
