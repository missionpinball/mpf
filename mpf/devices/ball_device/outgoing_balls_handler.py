"""Handles outgoing balls."""
import asyncio

from typing import Generator, Optional
from typing import List

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_count_handler import EjectTracker
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler
from mpf.devices.ball_device.incoming_balls_handler import IncomingBall

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.ball_device.ball_device import BallDevice


class OutgoingBall:

    """One outgoing ball."""

    __slots__ = ["max_tries", "eject_timeout", "target", "mechanical", "already_left"]

    def __init__(self, target: "BallDevice") -> None:
        """Initialise outgoing ball."""
        self.max_tries = None               # type: int
        self.eject_timeout = None           # type: int
        self.target = target                # type: BallDevice
        self.mechanical = None              # type: bool
        self.already_left = False           # type: bool


class OutgoingBallsHandler(BallDeviceStateHandler):

    """Handles all outgoing balls."""

    __slots__ = ["_eject_queue", "_current_target", "_cancel_future", "_incoming_ball_which_may_skip",
                 "_no_incoming_ball_which_may_skip", "_incoming_ball_which_may_skip_obj", "_eject_future"]

    def __init__(self, ball_device: "BallDevice") -> None:
        """Initialise outgoing balls handler."""
        super().__init__(ball_device)
        self._eject_queue = asyncio.Queue(loop=self.machine.clock.loop)     # type: asyncio.Queue
        self._current_target = None     # type: BallDevice
        self._cancel_future = None      # type: asyncio.Future
        self._incoming_ball_which_may_skip = asyncio.Event(loop=self.machine.clock.loop)
        self._incoming_ball_which_may_skip.clear()
        self._no_incoming_ball_which_may_skip = asyncio.Event(loop=self.machine.clock.loop)
        self._no_incoming_ball_which_may_skip.set()
        self._incoming_ball_which_may_skip_obj = []     # type: List[IncomingBall]
        self._eject_future = None       # type: asyncio.Future

    def add_eject_to_queue(self, eject: OutgoingBall):
        """Add an eject request to queue."""
        self._eject_queue.put_nowait(eject)

    def add_incoming_ball_which_may_skip(self, incoming_ball: IncomingBall):
        """Add incoming ball which may skip the device."""
        self._incoming_ball_which_may_skip_obj.append(incoming_ball)
        self._no_incoming_ball_which_may_skip.clear()
        self._incoming_ball_which_may_skip.set()

    def remove_incoming_ball_which_may_skip(self, incoming_ball: IncomingBall):
        """Remove incoming ball which may skip the device."""
        self._incoming_ball_which_may_skip_obj.remove(incoming_ball)
        if not self._incoming_ball_which_may_skip_obj:
            self._incoming_ball_which_may_skip.clear()
            self._no_incoming_ball_which_may_skip.set()

    @property
    def is_idle(self):
        """Return true if idle."""
        return not self._current_target and self._eject_queue.empty()

    @property
    def is_ready_to_receive(self):
        """Return true if we can receive balls."""
        return not self._current_target or not self._current_target.is_playfield() or not self._eject_future

    @asyncio.coroutine
    def wait_for_ready_to_receive(self):
        """Wait until the outgoing balls handler is ready to receive."""
        # if we are ejecting to a playfield wait until the eject finished because we cannot properly confirm otherwise
        if not self.is_ready_to_receive:
            self.debug_log("Wait for eject to finish")
            yield from self._eject_future
            self.debug_log("Eject finished")

    @asyncio.coroutine
    def _run(self):
        """Wait for eject queue."""
        while True:
            self._current_target = None
            self.ball_device.set_eject_state("idle")
            self.debug_log("Waiting for eject request.")
            eject_queue_future = Util.ensure_future(self._eject_queue.get(), loop=self.machine.clock.loop)
            incoming_ball_which_may_skip = self._incoming_ball_which_may_skip.wait()
            event = yield from Util.first([eject_queue_future, incoming_ball_which_may_skip],
                                          loop=self.machine.clock.loop)

            if event == eject_queue_future:
                eject_request = yield from event
                self._current_target = eject_request.target
                self.debug_log("Got eject request")

                if eject_request.already_left:
                    ball_eject_process = yield from self.ball_device.ball_count_handler.start_eject(already_left=True)
                    # no prepare eject because this cannot be blocked
                    yield from self._post_ejecting_event(eject_request, 1)
                    incoming_ball_at_target = self._add_incoming_ball_to_target(eject_request.target)
                    result = yield from self._handle_confirm(eject_request, ball_eject_process,
                                                             incoming_ball_at_target, 1)
                    if result:
                        yield from self.ball_device.ball_count_handler.end_eject(ball_eject_process, True)
                        continue

                if not (yield from self._ejecting(eject_request)):
                    return
            else:
                yield from self._skipping_ball(self.ball_device.config['eject_targets'][0], True)

    @asyncio.coroutine
    def _skipping_ball(self, target: "BallDevice", add_ball_to_target: bool):
        incoming_skipping_ball = self._incoming_ball_which_may_skip_obj[0]
        self.debug_log("Expecting incoming ball which may skip the device.")
        eject_request = OutgoingBall(target)
        yield from self._post_ejecting_event(eject_request, 1)
        incoming_ball_at_target = self._add_incoming_ball_to_target(eject_request.target)
        confirm_future = Util.ensure_future(incoming_ball_at_target.wait_for_confirm(), self.machine.clock.loop)
        ball_future = Util.ensure_future(self.ball_device.ball_count_handler.wait_for_ball(), self.machine.clock.loop)
        no_incoming_future = Util.ensure_future(self._no_incoming_ball_which_may_skip.wait(), self.machine.clock.loop)
        futures = [confirm_future, no_incoming_future, ball_future]
        if self._cancel_future:
            futures.append(self._cancel_future)

        if target.is_playfield():
            timeout = self.ball_device.config['eject_timeouts'][target] / 1000
        else:
            timeout = None

        try:
            event = yield from Util.first(futures, timeout=timeout, loop=self.machine.clock.loop)
        except asyncio.TimeoutError:
            event = confirm_future

        # if we got an confirm
        if event == confirm_future:
            self.debug_log("Got confirm for skipping ball.")
            yield from self._handle_eject_success(eject_request)
            incoming_skipping_ball.ball_arrived()
            if add_ball_to_target:
                target.available_balls += 1
            return True
        else:
            target.remove_incoming_ball(incoming_ball_at_target)
            yield from self._failed_eject(eject_request, 1, True)

        self.debug_log("No longer expecting incoming ball which may skip the device.")
        return False

    def find_available_ball_in_path(self, start: "BallDevice") -> bool:
        """Try to remove available ball at the end of the path."""
        if self._current_target == start:
            self.debug_log("Loop detected. Path will not go anywhere.")
            return False

        if not self._current_target and self.ball_device.available_balls > 0:
            self.debug_log("We do not have an eject but an available ball.")
            return True

        if self._current_target.is_playfield():
            self.debug_log("End of path is playfield %s", self._current_target)
            return True

        if self._current_target:
            return self._current_target.find_available_ball_in_path(start)

        self.ball_device.log.warning("No eject and no available_balls. Path went nowhere.")
        return False

    def cancel_path_if_target_is(self, start: "BallDevice", target: "BallDevice") -> bool:
        """Check if the ball is going to a certain target and cancel the path in that case.

        Args:
            target: Target to check

        Returns: True if found and deleted.
        """
        if self._current_target == start:
            self.debug_log("Loop detected. Path will not go anywhere.")
            return False

        # TODO: check queue entries
        if not self._cancel_future or self._cancel_future.done():
            # we cannot cancel anyway so do not even check further
            self.debug_log("Cancel path if target is not %s failed. Cannot cancel eject.", target.name)
            return False

        if not self._current_target:
            # no current target -> success we are not ejecting to the target
            self.debug_log("Cancel path if target is not %s failed. No current target.", target.name)
            return False

        if self._current_target == target:
            self.debug_log("Cancel path if target is not %s successful.", target.name)
            target.available_balls -= 1
            self._cancel_future.set_result(True)
            return True

        if not self._current_target.is_playfield() and self._current_target.cancel_path_if_target_is(start, target):
            # our successors are ejecting to target. cancel eject
            self.debug_log("Cancel path if target is not %s successful at successors.", target.name)
            self._cancel_future.set_result(True)
            return True

        # default false
        self.debug_log("Cancel path if target is not %s failed. We got another target.", target.name)
        return False

    @asyncio.coroutine
    # pylint: disable-msg=inconsistent-return-statements
    def _ejecting(self, eject_request: OutgoingBall):
        """Perform main eject loop."""
        eject_try = 0
        while True:
            # make sure the count is currently valid. process incoming and lost balls
            yield from self.ball_device.ball_count_handler.wait_for_count_is_valid()

            # prevent physical races with eject confirm
            if self._current_target.is_playfield() and not self.ball_device.ball_count_handler.is_full:
                yield from self.ball_device.incoming_balls_handler.wait_for_no_incoming_balls()

            if not self.ball_device.ball_count_handler.has_ball:
                # wait until we have a ball
                self._cancel_future = asyncio.Future(loop=self.machine.clock.loop)
                ball_future = Util.ensure_future(self.ball_device.ball_count_handler.wait_for_ball(),
                                                 loop=self.machine.clock.loop)
                skipping_ball_future = Util.ensure_future(self._incoming_ball_which_may_skip.wait(),
                                                          loop=self.machine.clock.loop)

                self.ball_device.set_eject_state("waiting_for_ball")
                result = yield from Util.first([self._cancel_future, ball_future, skipping_ball_future],
                                               loop=self.machine.clock.loop)

                if result == skipping_ball_future:
                    self._cancel_future = asyncio.Future(loop=self.machine.clock.loop)
                    result = yield from self._skipping_ball(self._current_target, False)
                    if result or self._cancel_future.done() and not self._cancel_future.cancelled():
                        self._cancel_future = None
                        return True
                    else:
                        self._cancel_future.cancel()
                        self._cancel_future = None
                        continue

                if self._cancel_future.done() and not self._cancel_future.cancelled():
                    # eject cancelled
                    self._cancel_future = None
                    return True
                self._cancel_future.cancel()
                self._cancel_future = None

            self.ball_device.set_eject_state("waiting_for_target_ready")

            # inform targets about the eject (can delay the eject)
            yield from self._prepare_eject(eject_request, eject_try)
            # wait for target to be ready
            # TODO: block one spot in target device to prevent double eject
            yield from eject_request.target.wait_for_ready_to_receive(self.ball_device)
            self.ball_device.set_eject_state("ejecting")
            self._eject_future = asyncio.Future(loop=self.machine.clock.loop)
            result = yield from self._eject_ball(eject_request, eject_try)
            self._eject_future.set_result(result)
            self._eject_future = None
            if result:
                # eject is done. return to main loop
                return True

            eject_try += 1

            if eject_request.max_tries and eject_try >= eject_request.max_tries:
                # stop device
                self.ball_device.set_eject_state("eject_broken")
                yield from self._failed_eject(eject_request, eject_try, False)
                self.machine.events.post("balldevice_{}_broken".format(self.ball_device.name))
                '''event: balldevice_(name)_broken

                desc: The ball device called "name" is broken and will no longer operate.
                '''
                self._task.cancel()
                return False
            else:
                yield from self._failed_eject(eject_request, eject_try, True)

    @asyncio.coroutine
    def _prepare_eject(self, eject_request: OutgoingBall, eject_try: int):
        yield from self.machine.events.post_queue_async(
            'balldevice_{}_ball_eject_attempt'.format(self.ball_device.name),
            balls=1,
            target=eject_request.target,
            source=self.ball_device,
            mechanical_eject=eject_request.mechanical,
            num_attempts=eject_try)
        '''event: balldevice_(name)_ball_eject_attempt

        desc: The ball device called "name" is attempting to eject a ball (or
        balls). This is a queue event. The eject will not actually be attempted
        until the queue is cleared.

        args:

        balls: The number of balls that are to be ejected.
        taget: The target ball device that will receive these balls.
        source: The source device that will be ejecting the balls.
        mechanical_eject: Boolean as to whether this is a mechanical eject.
        num_attempts: How many eject attempts have been tried so far.
        '''

    @asyncio.coroutine
    def _failed_eject(self, eject_request: OutgoingBall, eject_try: int, retry: bool):
        yield from self.machine.events.post_async(
            'balldevice_' + self.ball_device.name + '_ball_eject_failed',
            target=eject_request.target,
            balls=1,
            retry=retry,
            num_attempts=eject_try)
        '''event: balldevice_(name)_ball_eject_failed
        desc: A ball (or balls) has failed to eject from the device (name).
        args:
            target: The target device that was supposed to receive the ejected
                balls.
            balls: The number of balls that failed to eject.
            retry: Boolean as to whether this eject will be retried.
            num_attempts: How many attemps have been made to eject this ball
                (or balls).
        '''

    @asyncio.coroutine
    def _post_ejecting_event(self, eject_request: OutgoingBall, eject_try: int):
        yield from self.machine.events.post_async(
            'balldevice_{}_ejecting_ball'.format(self.ball_device.name),
            balls=1,
            target=eject_request.target,
            source=self.ball_device,
            mechanical_eject=eject_request.mechanical,
            num_attempts=eject_try)
        '''event: balldevice_(name)_ejecting_ball

        desc: The ball device called "name" is ejecting a ball right now.

        args:

        balls: The number of balls that are to be ejected.
        taget: The target ball device that will receive these balls.
        source: The source device that will be ejecting the balls.
        mechanical_eject: Boolean as to whether this is a mechanical eject.
        num_attempts: How many eject attempts have been tried so far.
        '''

    @asyncio.coroutine
    def _eject_ball(self, eject_request: OutgoingBall, eject_try: int) -> Generator[int, None, bool]:
        # inform the counter that we are ejecting now
        self.info_log("Ejecting ball to %s", eject_request.target)
        yield from self._post_ejecting_event(eject_request, eject_try)
        ball_eject_process = yield from self.ball_device.ball_count_handler.start_eject()
        try:
            yield from ball_eject_process.will_eject()
            self.debug_log("Wait for ball to leave device")
            # eject the ball

            ball_left = ball_eject_process.wait_for_ball_left()
            waiters = [ball_left]
            trigger = None
            tilt = None
            if self.ball_device.ejector:
                # eject on tilt
                if eject_request.mechanical:
                    tilt = self.machine.events.wait_for_event("tilt")
                    waiters.append(tilt)

                # wait for trigger event
                if eject_request.mechanical and self.ball_device.config['player_controlled_eject_event']:
                    trigger = self.machine.events.wait_for_event(
                        self.ball_device.config['player_controlled_eject_event'])
                    waiters.append(trigger)
                elif eject_request.mechanical and self.ball_device.config['mechanical_eject']:
                    # do nothing
                    pass
                else:
                    yield from self.ball_device.ejector.eject_one_ball(ball_eject_process.is_jammed(), eject_try)

            # wait until the ball has left
            if (self.ball_device.config['mechanical_eject'] or
                    self.ball_device.config['player_controlled_eject_event']) and eject_request.mechanical:
                timeout = None
            else:
                timeout = eject_request.eject_timeout
            try:
                yield from Util.any(waiters, timeout=timeout, loop=self.machine.clock.loop)
            except asyncio.TimeoutError:
                # timeout. ball did not leave. failed
                yield from self.ball_device.ball_count_handler.end_eject(ball_eject_process, False)
                return False

            if (trigger and trigger.done()) or (tilt and tilt.done()):
                yield from self.ball_device.ejector.eject_one_ball(ball_eject_process.is_jammed(), eject_try)
                # TODO: add timeout here
                yield from ball_left

            self.ball_device.set_eject_state("ball_left")
            self.debug_log("Ball left")
            incoming_ball_at_target = self._add_incoming_ball_to_target(eject_request.target)
            result = yield from self._handle_confirm(eject_request, ball_eject_process, incoming_ball_at_target,
                                                     eject_try)
            yield from self.ball_device.ball_count_handler.end_eject(ball_eject_process, result)
            return result
        except asyncio.CancelledError:
            ball_eject_process.cancel()
            raise

    def _add_incoming_ball_to_target(self, target: "BallDevice") -> IncomingBall:
        # we are the source of this ball
        incoming_ball_at_target = IncomingBall(self.ball_device, target)
        if self.ball_device.config['confirm_eject_type'] == "switch":
            incoming_ball_at_target.add_external_confirm_switch(self.ball_device.config['confirm_eject_switch'].name)
        elif self.ball_device.config['confirm_eject_type'] == "event":
            incoming_ball_at_target.add_external_confirm_event(self.ball_device.config['confirm_eject_event'])

        target.add_incoming_ball(incoming_ball_at_target)
        return incoming_ball_at_target

    @asyncio.coroutine
    def _handle_confirm(self, eject_request: OutgoingBall, ball_eject_process: EjectTracker,
                        incoming_ball_at_target: IncomingBall, eject_try: int) -> Generator[int, None, bool]:
        # TODO: check double eject (two balls left). can only happen when not jammed
        timeout = eject_request.eject_timeout
        self.debug_log("Wait for confirm with timeout %s", timeout)
        confirm_future = incoming_ball_at_target.wait_for_confirm()
        try:
            yield from Util.first([confirm_future], timeout=timeout,
                                  loop=self.machine.clock.loop, cancel_others=False)
        except asyncio.TimeoutError:
            self.ball_device.set_eject_state("failed_confirm")
            self.debug_log("Got timeout (%ss) before confirm from %s", timeout, eject_request.target)
            return (yield from self._handle_late_confirm_or_missing(eject_request, ball_eject_process,
                                                                    incoming_ball_at_target, eject_try))
        else:
            if not confirm_future.done():
                raise AssertionError("Future not done")
            if confirm_future.cancelled():
                raise AssertionError("Eject failed but should not")
            # eject successful
            self.debug_log("Got eject confirm")
            yield from self._handle_eject_success(eject_request)
            return True

    # pylint: disable-msg=too-many-arguments
    @asyncio.coroutine
    def _handle_playfield_timeout_confirm(self, eject_request, ball_return_future, unknown_balls_future,
                                          incoming_ball_at_target):
        yield from asyncio.sleep(0.1, loop=self.machine.clock.loop)

        if not ball_return_future.done() and not unknown_balls_future.done():
            # if target is playfield mark eject as confirmed
            self.debug_log("Confirming eject because target is playfield and ball did not return.")
            incoming_ball_at_target.ball_arrived()
            yield from self._handle_eject_success(eject_request)
            return True

        return False

    @asyncio.coroutine
    def _handle_late_confirm_or_missing(self, eject_request: OutgoingBall, ball_eject_process: EjectTracker,
                                        incoming_ball_at_target: IncomingBall,
                                        eject_try: int) -> Generator[int, None, bool]:
        ball_return_future = Util.ensure_future(ball_eject_process.wait_for_ball_return(), loop=self.machine.clock.loop)
        unknown_balls_future = Util.ensure_future(ball_eject_process.wait_for_ball_unknown_ball(),
                                                  loop=self.machine.clock.loop)
        eject_success_future = incoming_ball_at_target.wait_for_confirm()
        timeout = self.ball_device.config['ball_missing_timeouts'][eject_request.target] / 1000

        # if ball_eject_process.is_jammed():
        #     # ball returned. eject failed
        #     eject_request.already_left = False
        #     incoming_ball_at_target.did_not_arrive()
        #     return False

        # assume that the ball may have skipped the target device by now
        incoming_ball_at_target.set_can_skip()

        if not eject_request.target.is_playfield():
            yield from eject_request.target.ball_count_handler.wait_for_count_is_valid()
            if eject_success_future.done():
                self.debug_log("Got eject confirm (after recounting)")
                yield from self._handle_eject_success(eject_request)
                return True
        else:
            if (yield from self._handle_playfield_timeout_confirm(
                    eject_request, ball_return_future, unknown_balls_future,
                    incoming_ball_at_target)):
                return True

        try:
            event = yield from Util.first([ball_return_future, unknown_balls_future, eject_success_future],
                                          timeout=timeout, loop=self.machine.clock.loop)
        except asyncio.TimeoutError:
            # handle lost ball
            incoming_ball_at_target.did_not_arrive()
            yield from self._failed_eject(eject_request, eject_try, True)
            yield from self.ball_device.lost_ejected_ball(target=eject_request.target)
            # ball is lost but the eject is finished -> return true
            return True
        else:
            if event == eject_success_future:
                # we eventually got eject success
                yield from self._handle_eject_success(eject_request)
                return True
            elif event == ball_return_future:
                # ball returned. eject failed
                self.debug_log("Ball returned. Eject failed.")
                eject_request.already_left = False
                incoming_ball_at_target.did_not_arrive()
                return False
            elif event == unknown_balls_future:
                # TODO: this may be an option
                self.debug_log("Got unknown balls. Assuming a ball returned.")
                incoming_ball_at_target.did_not_arrive()
                return False
        # throw an error if we got here
        raise AssertionError("Invalid state")

    @asyncio.coroutine
    def _handle_eject_success(self, eject_request: OutgoingBall):
        self.debug_log("Eject successful")

        yield from self.machine.events.post_async('balldevice_' + self.ball_device.name +
                                                  '_ball_eject_success',
                                                  balls=1,
                                                  target=eject_request.target)
        '''event: balldevice_(name)_ball_eject_success
        desc: One or more balls has successfully ejected from the device
            (name).
        args:
            balls: The number of balls that have successfully ejected.
            target: The target device that has received (or will be receiving)
                the ejected ball(s).
        '''
