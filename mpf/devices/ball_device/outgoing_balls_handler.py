"""Handles outgoing balls."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_count_handler import EjectTracker
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler
from mpf.devices.ball_device.incoming_balls_handler import IncomingBall


class OutgoingBall:

    """One outgoing ball."""

    def __init__(self):
        self.max_tries = None
        self.eject_timeout = None
        self.target = None
        self.mechanical = None
        self.already_left = False


class OutgoingBallsHandler(BallDeviceStateHandler):

    """Handles all outgoing balls."""

    def __init__(self, ball_device):
        super().__init__(ball_device)
        self._eject_queue = asyncio.Queue(loop=self.machine.clock.loop)
        self._state = "idle"
        self._current_target = None
        self._cancel_future = None

    def add_eject_to_queue(self, eject: OutgoingBall):
        """Add an eject request to queue."""
        self._eject_queue.put_nowait(eject)

    @asyncio.coroutine
    def _run(self):
        """Wait for eject queue."""
        while True:
            eject_queue_future = self.ball_device.ensure_future(self._eject_queue.get())
            eject_request = yield from eject_queue_future

            self.debug_log("Got eject request")

            if eject_request.already_left:
                ball_eject_process = yield from self.ball_device.ball_count_handler.start_eject(already_left=True)
                # no prepare eject because this cannot be blocked
                yield from self._post_ejecting_event(eject_request, 1)
                incoming_ball_at_target = self._add_incoming_ball_to_target(eject_request)
                result = yield from self._handle_confirm(eject_request, ball_eject_process, incoming_ball_at_target)
                if result:
                    continue

            if not (yield from self._ejecting(eject_request)):
                return
            self._state = "idle"

    @property
    def state(self):
        """Return the current state for legacy reasons."""
        return self._state

    def cancel_path_if_target_is(self, target) -> bool:
        """Check if the ball is going to a certain target and cancel the path in that case.

        Args:
            target: Target to check

        Returns: True if found and deleted.
        """
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

        if not self._current_target.is_playfield() and self._current_target.cancel_path_if_target_is_not(target):
            # our successors are ejecting to target. cancel eject
            self.debug_log("Cancel path if target is not %s successful at successors.", target.name)
            self._cancel_future.set_result(True)
            return True

        # default false
        self.debug_log("Cancel path if target is not %s failed. We got another target.", target.name)
        return False

    @asyncio.coroutine
    def _ejecting(self, eject_request: OutgoingBall):
        """Perform main eject loop."""
        # TODO: handle unexpected mechanical eject
        eject_try = 0
        while True:
            self._current_target = eject_request.target
            self._cancel_future = asyncio.Future(loop=self.machine.clock.loop)
            # wait until we have a ball (might be instant)
            self._state = "waiting_for_ball"
            self.debug_log("Waiting for ball")
            yield from Util.first([self._cancel_future, self.ball_device.ball_count_handler.wait_for_ball()],
                                  loop=self.machine.clock.loop)
            if self._cancel_future.done() and not self._cancel_future.cancelled():
                # eject cancelled
                return True
            self._cancel_future = None

            # inform targets about the eject (can delay the eject)
            yield from self._prepare_eject(eject_request, eject_try)
            # wait for target to be ready
            # TODO: block one spot in target device to prevent double eject
            yield from eject_request.target.wait_for_ready_to_receive()
            # check if we still have a ball
            ball_count = yield from self.ball_device.ball_count_handler.get_ball_count()
            if ball_count == 0:
                # abort the eject because ball was lost in the meantime
                # TODO: might be mechanical eject
                yield from self._abort_eject(eject_request, eject_try)
                # try again
                continue
            self._state = "ejecting"
            result = yield from self._eject_ball(eject_request, eject_try)
            if result:
                # eject is done. return to main loop
                return True

            yield from self._failed_eject(eject_request, eject_try)
            eject_try += 1

            if eject_request.max_tries and eject_try >= eject_request.max_tries:
                # stop device
                self._state = "eject_broken"
                self.ball_device.stop()
                # TODO: inform machine about broken device
                return False

    @asyncio.coroutine
    def _prepare_eject(self, eject_request: OutgoingBall, eject_try):
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
    def _abort_eject(self, eject_request: OutgoingBall, eject_try):
        self.debug_log("Aborting eject. Lost ball while waiting for target to become ready.")
        pass

    @asyncio.coroutine
    def _failed_eject(self, eject_request: OutgoingBall, eject_try):
        pass

    @asyncio.coroutine
    def _post_ejecting_event(self, eject_request: OutgoingBall, eject_try):
        yield from self.machine.events.post_async(
            'balldevice_{}_ejecting_ball'.format(self.ball_device.name),
            balls=1,
            target=eject_request.target,
            source=self,
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
    def _eject_ball(self, eject_request: OutgoingBall, eject_try) -> bool:
        # inform the counter that we are ejecting now
        self.debug_log("Ejecting ball to %s", eject_request.target)
        yield from self._post_ejecting_event(eject_request, eject_try)
        ball_eject_process = yield from self.ball_device.ball_count_handler.start_eject()
        self.debug_log("Wait for ball to leave device")
        # eject the ball

        ball_left = ball_eject_process.wait_for_ball_left()
        waiters = [ball_left]
        trigger = None
        if self.ball_device.ejector:
            # wait for trigger event
            if eject_request.mechanical and self.ball_device.config['player_controlled_eject_event']:
                trigger = self.machine.events.wait_for_event(self.ball_device.config['player_controlled_eject_event'])
                waiters.append(trigger)
            else:
                self.ball_device.ejector.eject_one_ball(ball_eject_process.is_jammed(), eject_try)

        # wait until the ball has left
        if (self.ball_device.config['mechanical_eject'] or self.ball_device.config['player_controlled_eject_event']) and \
                eject_request.mechanical:
            timeout = None
        else:
            timeout = eject_request.eject_timeout
        try:
            yield from Util.any(waiters, timeout=timeout, loop=self.machine.clock.loop)
        except asyncio.TimeoutError:
            # timeout. ball did not leave. failed
            ball_eject_process.ball_returned()
            return False

        if trigger and trigger.done():
            self.ball_device.ejector.eject_one_ball(ball_eject_process.is_jammed(), eject_try)
            # TODO: add timeout here
            yield from ball_left

        self._state = "ball_left"
        self.debug_log("Ball left")
        incoming_ball_at_target = self._add_incoming_ball_to_target(eject_request)
        return (yield from self._handle_confirm(eject_request, ball_eject_process, incoming_ball_at_target))

    def _add_incoming_ball_to_target(self, eject_request: OutgoingBall) -> IncomingBall:
        incoming_ball_at_target = IncomingBall()
        # we are the source of this ball
        incoming_ball_at_target.source = self.ball_device
        # there is no timeout
        incoming_ball_at_target.timeout_future = asyncio.Future(loop=self.machine.clock.loop)
        # we will wait on this future
        incoming_ball_at_target.confirm_future = asyncio.Future(loop=self.machine.clock.loop)
        eject_request.target.add_incoming_ball(incoming_ball_at_target)
        return incoming_ball_at_target

    def _remove_incoming_ball_at_target(self, eject_request: OutgoingBall, incoming_ball_at_target: IncomingBall):
        eject_request.target.remove_incoming_ball(incoming_ball_at_target)
        incoming_ball_at_target.timeout_future.cancel()

    @asyncio.coroutine
    def _handle_confirm(self, eject_request: OutgoingBall, ball_eject_process: EjectTracker,
                        incoming_ball_at_target: IncomingBall) -> bool:
        # TODO: check double eject (two balls left)
        timeout = eject_request.eject_timeout
        self.debug_log("Wait for confirm with timeout %s", timeout)
        try:
            yield from Util.first([incoming_ball_at_target.confirm_future], timeout=timeout,
                                  loop=self.machine.clock.loop, cancel_others=False)
        except asyncio.TimeoutError:
            self._state = "failed_confirm"
            self.debug_log("Got timeout before confirm")
            return (yield from self._handle_late_confirm_or_missing(eject_request, ball_eject_process,
                                                                    incoming_ball_at_target))
        else:
            if not incoming_ball_at_target.confirm_future.done():
                raise AssertionError("Future not done")
            if incoming_ball_at_target.confirm_future.cancelled():
                raise AssertionError("Eject failed but should not")
            # eject successful
            self.debug_log("Got eject confirm")
            yield from self._handle_eject_success(ball_eject_process, eject_request)
            return True

    @asyncio.coroutine
    def _handle_late_confirm_or_missing(self, eject_request: OutgoingBall, ball_eject_process: EjectTracker,
                                        incoming_ball_at_target: IncomingBall) -> bool:
        ball_return_future = self.ball_device.ensure_future(ball_eject_process.wait_for_ball_return())
        unknown_balls_future = self.ball_device.ensure_future(ball_eject_process.wait_for_ball_unknown_ball())
        eject_success_future = incoming_ball_at_target.confirm_future
        timeout = 30    # TODO: make this dynamic

        # TODO: remove hack when moving code below
        yield from asyncio.sleep(0.1, loop=self.machine.clock.loop)

        # TODO: move this to a better location
        if not ball_return_future.done() and not unknown_balls_future.done() and eject_request.target.is_playfield():
            # if target is playfield mark eject as confirmed
            self.debug_log("Confirming eject because target is playfield and ball did not return.")
            incoming_ball_at_target.confirm_future.set_result(True)
            eject_request.target.remove_incoming_ball(incoming_ball_at_target)

        # TODO: timeout
        try:
            event = yield from Util.first([ball_return_future, unknown_balls_future, eject_success_future],
                                          timeout=timeout, loop=self.machine.clock.loop)
        except asyncio.TimeoutError:
            # handle lost ball
            self._remove_incoming_ball_at_target(eject_request, incoming_ball_at_target)
            ball_eject_process.ball_lost()
            yield from self.ball_device.lost_ejected_ball(target=eject_request.target)
            # ball is lost but the eject is finished -> return true
            return True
        else:
            if event == eject_success_future:
                # we eventually got eject success
                yield from self._handle_eject_success(ball_eject_process, eject_request)
                return True
            elif event == ball_return_future:
                # ball returned. eject failed
                eject_request.already_left = False
                ball_eject_process.ball_returned()
                return False
            elif event == unknown_balls_future:
                # TODO: this may be an option
                self.debug_log("Got unknown balls. Assuming a ball returned.")
                self._remove_incoming_ball_at_target(eject_request, incoming_ball_at_target)
                ball_eject_process.ball_returned()
            else:
                raise AssertionError("Invalid state")

    @asyncio.coroutine
    def _handle_eject_success(self, ball_eject_process: EjectTracker, eject_request: OutgoingBall):
        self.debug_log("Eject successful")
        ball_eject_process.eject_success()
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
