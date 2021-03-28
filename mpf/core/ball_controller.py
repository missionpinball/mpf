"""Contains the BallController class which manages and tracks all the balls in a pinball machine."""

import asyncio
from typing import Union, Iterable, Optional

from mpf.devices.ball_device.ball_device import BallDevice

from mpf.core.delays import DelayManager
from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util
from mpf.core.mpf_controller import MpfController


class BallController(MpfController):

    """Tracks and manages all the balls in a pinball machine."""

    config_name = "ball_controller"

    __slots__ = ["delay", "num_balls_known", "_add_new_balls_task", "_captured_balls"]

    def __init__(self, machine: MachineController) -> None:
        """Initialise ball controller.

        Args:
        ----
            machine : :class:`MachineController`. A reference to the instance
                of the MachineController object.

        """
        super().__init__(machine)

        self.delay = DelayManager(self.machine)

        self.num_balls_known = 0

        # register for events
        self.machine.events.add_handler('request_to_start_game',
                                        self.request_to_start_game)
        self.machine.events.add_handler('init_phase_2',
                                        self._initialize)
        self.machine.events.add_handler('init_phase_4',
                                        self._init4, priority=100)

        self.machine.events.add_handler('shutdown',
                                        self._stop)

        self._add_new_balls_task = None                                         # type: Optional[asyncio.Task]
        self._captured_balls = asyncio.Queue()      # type: asyncio.Queue

    def _init4(self, **kwargs):
        del kwargs

        # see if there are non-playfield devices
        for device in self.machine.ball_devices.values():
            if device.is_playfield():
                continue
            # found a device
            break
        else:
            # there is no non-playfield device. end this.
            return

        self._add_new_balls_task = self.machine.clock.loop.create_task(self._add_new_balls_to_playfield())
        self._add_new_balls_task.add_done_callback(Util.raise_exceptions)

    def _stop(self, **kwargs) -> None:
        del kwargs
        if self._add_new_balls_task:
            self._add_new_balls_task.cancel()
            self._add_new_balls_task = None

    def _get_total_balls_in_devices(self) -> int:
        """Return the total ball count over all devices in the machine."""
        balls = 0
        # get count for all ball devices
        for device in self.machine.ball_devices.values():
            if device.is_playfield():
                continue

            balls += device.ball_count_handler.counter.count_balls_sync()
        return balls

    def add_captured_ball(self, source: BallDevice) -> None:
        """Inform ball controller about a captured ball (which might be new)."""
        self._captured_balls.put_nowait(source)

    async def _add_new_balls_to_playfield(self) -> None:
        # initial count
        self.num_balls_known = await self._count_all_balls_in_devices()
        self.info_log("Initial balls found: %s", self.num_balls_known)

        while True:
            capture = await self._captured_balls.get()
            balls = await self._count_all_balls_in_devices()
            if balls > self.num_balls_known:
                self.num_balls_known += 1
                capture.balls += 1
                capture.available_balls += 1
                self.info_log("Found a new ball which was captured from %s. Known balls: %s", capture.name,
                              self.num_balls_known)
                self.machine.events.post("found_new_ball")

            if len(self.machine.playfields) > 1:
                self._balance_playfields()

    def _balance_playfields(self) -> None:
        # find negative counts
        for playfield_target in self.machine.playfields.values():
            if playfield_target.balls < 0:
                for playfield_source in self.machine.playfields.values():
                    if playfield_source.balls > 0:
                        playfield_source.balls -= 1
                        playfield_source.available_balls -= 1
                        playfield_target.balls += 1
                        playfield_target.available_balls += 1
                        # post event
                        self.machine.events.post("playfield_jump", source=playfield_source, target=playfield_target)
                        break

    async def _count_all_balls_in_devices(self) -> int:
        """Count balls in all devices."""
        while True:
            # wait until all devices are stable
            # prepare futures in case we have to wait to prevent race between count and building futures
            futures = []
            for device in self.machine.ball_devices.values():
                if not device.is_playfield():
                    futures.append(asyncio.ensure_future(device.ball_count_handler.counter.wait_for_count_stable()))

            try:
                return self._get_total_balls_in_devices()
            except ValueError:
                await asyncio.wait(futures)
                continue

    def _count_balls(self) -> int:
        """Count balls in devices and raise ValueError if counts are not stable."""
        self.debug_log("Counting Balls")
        balls = 0

        for device in self.machine.ball_devices.values():
            # skip playfields
            if device.is_playfield():
                continue
            if device.ball_count_handler.counter.config.get('ball_switches'):
                for switch in device.ball_count_handler.counter.config['ball_switches']:
                    if self.machine.switch_controller.is_active(
                            switch, ms=device.ball_count_handler.counter.config['entrance_count_delay']):
                        balls += 1
                    elif self.machine.switch_controller.is_inactive(
                            switch, ms=device.ball_count_handler.counter.config['exit_count_delay']):
                        continue
                    else:
                        raise ValueError("switches not stable")
            elif 'trough' in device.tags:
                # special handling for troughs (needed for gottlieb)
                balls += device.balls

        return balls

    def _initialize(self, **kwargs) -> None:
        """Initialise ball controller."""
        # If there are no ball devices, then the ball controller has no work to
        # do and will create errors, so we just abort.
        del kwargs
        if not hasattr(self.machine, 'ball_devices'):
            return

        for device in self.machine.ball_devices.values():
            priority = 0
            if 'drain' in device.tags or 'trough' in device.tags:  # device is used to drain balls from pf
                priority += 1   # order handlers
                self.machine.events.add_handler('balldevice_' + device.name +
                                                '_ball_enter',
                                                self._ball_drained_handler, priority=20 + priority)

    def dump_ball_counts(self) -> None:
        """Dump ball count of all devices."""
        self.info_log("Known balls: %s", self.num_balls_known)
        for device in self.machine.ball_devices.values():
            self.info_log("%s contains %s balls. Tags %s", device.name, device.balls, device.tags)

    def request_to_start_game(self, **kwargs) -> bool:
        """Handle result of the *request_to_start_game* event.

        Checks to make sure that the balls are in all the right places and
        returns. If too many balls are missing (based on the config files 'Min
        Balls' setting), it will return False to reject the game start request.
        """
        del kwargs
        try:
            balls = self._count_balls()
        except ValueError:
            balls = -1
        self.debug_log("Received request to start game.")
        if balls < self.machine.config['machine']['min_balls']:
            self.dump_ball_counts()
            self.warning_log("BallController denies game start. Not enough "
                             "balls. %s found. %s required", balls, self.machine.config['machine']['min_balls'])

            self.info_log("Triggering ball search.")
            for playfield in self.machine.playfields.values():
                playfield.ball_search.enable()
                playfield.ball_search.start()
            return False

        if self.machine.config['game']['allow_start_with_ball_in_drain']:
            allowed_positions = ['home', 'trough', 'drain']
        else:
            allowed_positions = ['home', 'trough']

        if (not self.machine.config['game']['allow_start_with_loose_balls'] and
                not self.are_balls_collected(allowed_positions)):
            self.collect_balls('home')
            self.dump_ball_counts()
            self.warning_log("BallController denies game start. Balls are not "
                             "in their home positions.")
            return False

        # allow start
        return True

    def are_balls_collected(self, target: Union[str, Iterable[str]]) -> bool:
        """Check to see if all the balls are contained in devices tagged with the parameter that was passed.

        Note if you pass a target that's not used in any ball devices, this
        method will return True. (Because you're asking if all balls are
        nowhere, and they always are. :)

        Args:
        ----
            target: String or list of strings of the tags you'd like to
                collect the balls to. Default of None will be replaced with
                'home' and 'trough'.
        """
        self.debug_log("Checking to see if all the balls are in devices tagged"
                       " with '%s'", target)

        if isinstance(target, str):
            target = Util.string_to_event_list(target)

        count = 0
        devices = set()

        for tag in target:
            for device in self.machine.ball_devices.items_tagged(tag):      # type: ignore
                devices.add(device)

        if not devices:
            # didn't find any devices matching that tag, so we return True
            return True

        for device in devices:
            count += device.balls
            self.debug_log('Found %s ball(s) in %s. Found %s total',
                           device.balls, device.name, count)

        if count == self.machine.ball_controller.num_balls_known:
            self.debug_log("Yes, all balls are collected")
            return True

        self.debug_log("No, all balls are not collected. Balls Counted: %s. "
                       "Total balls known: %s", count,
                       self.machine.ball_controller.num_balls_known)
        return False

    def collect_balls(self, target='home, trough') -> None:
        """Ensure that all balls are in contained in ball devices with the tag or list of tags you pass.

        Typically this would be used after a game ends, or when the machine is
        reset or first starts up, to ensure that all balls are in devices
        tagged with 'home' and/or 'trough'.

        Args:
        ----
            target: A string of the tag name or a list of tags names of the
                ball devices you want all the balls to end up in. Default is
                ['home', 'trough'].

        """
        tag_list = Util.string_to_event_list(target)

        self.debug_log("Collecting all balls to devices with tags '%s'",
                       tag_list)

        target_devices = set()
        source_devices = set()
        balls_to_collect = False

        for tag in tag_list:
            for device in self.machine.ball_devices.items_tagged(tag):      # type: ignore
                target_devices.add(device)

        for device in self.machine.ball_devices.values():
            if device not in target_devices:
                if device.available_balls:
                    source_devices.add(device)
                    balls_to_collect = True

        if balls_to_collect:
            self.debug_log("Ejecting all balls from: %s", source_devices)

            self.machine.events.post('collecting_balls')
            '''event: collecting_balls

            desc: Posted by the ball controller when it starts the collecting
                balls process.

            '''

            for device in target_devices:
                self.machine.events.remove_handler(self._collecting_balls_entered_callback)
                self.machine.events.add_handler(
                    'balldevice_{}_ball_enter'.format(device.name),
                    self._collecting_balls_entered_callback,
                    target=target, priority=10)

            for device in source_devices:
                if not device.is_playfield():
                    if "drain" in device.tags:
                        device.eject_all(device.find_next_trough())
                    else:
                        device.eject_all()
        else:
            self.debug_log("All balls are collected")
            self._collecting_balls_complete()

    def _collecting_balls_entered_callback(self, target: str, new_balls: int, unclaimed_balls: int, **kwargs) -> dict:
        del kwargs
        del new_balls
        if self.are_balls_collected(target=target):
            self._collecting_balls_complete()

        return {'unclaimed_balls': unclaimed_balls}

    def _collecting_balls_complete(self) -> None:
        self.machine.events.remove_handler(self._collecting_balls_entered_callback)
        self.machine.events.post('collecting_balls_complete')
        '''event: collecting_balls_complete

        desc: Posted by the ball controller when it has finished the collecting
            balls process.

        '''

    def _ball_drained_handler(self, new_balls: int, unclaimed_balls: int, device: BallDevice, **kwargs) -> None:
        del kwargs
        del new_balls
        self.machine.events.post_relay('ball_drain',
                                       device=device,
                                       balls=unclaimed_balls)
        '''event: ball_drain

        desc: A ball (or balls) has just drained. (More specifically, ball(s)
        have entered a ball device tagged with "drain".)

        This is a relay event.

        args:

        device: The ball device object that received the ball(s)

        balls: The number of balls that have just drained. Any balls remaining
        after the relay will be processed as newly-drained balls.

        '''
