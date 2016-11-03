"""Handles outgoing balls."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_count_handler import EjectProcessCounter
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler
from mpf.devices.ball_device.incoming_balls_handler import IncomingBall


class EjectRequest:

    """One eject request."""

    def __init__(self, machine):
        self.max_tries = None
        self.eject_timeout = None
        self.target = None
        self.mechanical = None
        self.confirm_future = asyncio.Future(loop=machine.clock.loop)

    def wait_for_eject_confirm(self):
        """Wait for eject confirmation."""
        return self.confirm_future


class OutgoingBallsHandler(BallDeviceStateHandler):

    """Handles all outgoing balls."""

    def __init__(self, ball_device):
        super().__init__(ball_device)
        self._eject_queue = asyncio.Queue(loop=self.machine.clock.loop)
        self._state = "idle"

    def add_eject_to_queue(self, eject: EjectRequest):
        """Add an eject request to queue."""
        self._eject_queue.put_nowait(eject)

    @asyncio.coroutine
    def _run(self):
        """Wait for eject queue."""
        while True:
            eject_queue_future = self.ball_device.ensure_future(self._eject_queue.get())
            eject_request = yield from eject_queue_future

            self.debug_log("Got eject request")

            yield from self._ejecting(eject_request)
            self._state = "idle"

    @property
    def state(self):
        """Return the current state for legacy reasons."""
        return self._state

    @asyncio.coroutine
    def _ejecting(self, eject_request: EjectRequest):
        """Perform main eject loop."""
        # TODO: handle unexpected mechanical eject
        eject_try = 0
        while True:
            # wait until we have a ball (might be instant)
            self._state = "waiting_for_ball"
            self.debug_log("Waiting for ball")
            yield from self.ball_device.ball_count_handler.wait_for_ball()
            # inform targets about the eject (can delay the eject)
            yield from self._prepare_eject(eject_request, eject_try)
            # wait for target to be ready
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
            self.debug_log("Ejecting ball")
            result = yield from self._eject_ball(eject_request, eject_try)
            if result:
                # eject is done. return to main loop
                return

            yield from self._failed_eject(eject_request, eject_try)
            eject_try += 1

            if eject_request.max_tries and eject_try > eject_request.max_tries:
                # stop device
                self.ball_device.stop()
                # TODO: inform machine about broken device
                return

    @asyncio.coroutine
    def _prepare_eject(self, eject_request: EjectRequest, eject_try):
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
    def _abort_eject(self, eject_request: EjectRequest, eject_try):
        pass

    @asyncio.coroutine
    def _failed_eject(self, eject_request: EjectRequest, eject_try):
        pass

    @asyncio.coroutine
    def _eject_ball(self, eject_request: EjectRequest, eject_try) -> bool:
        # inform the counter that we are ejecting now
        self.debug_log("Ejecting ball to %s", eject_request.target)
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
        ball_eject_process = self.ball_device.ball_count_handler.start_eject()
        self.debug_log("Wait for ball to leave device")
        # eject the ball
        if self.ball_device.ejector:
            self.ball_device.ejector.eject_one_ball(ball_eject_process.is_jammed(), eject_try)
        # wait until the ball has left
        timeout = eject_request.eject_timeout
        try:
            yield from Util.first([ball_eject_process.wait_for_ball_left()], timeout=timeout,
                                  loop=self.machine.clock.loop)
        except asyncio.TimeoutError:
            # timeout. ball did not leave. failed
            ball_eject_process.ball_returned()
            return False
        else:
            self._state = "ball_left"
            self.debug_log("Ball left")
            incoming_ball_at_target = self._add_incoming_ball_to_target(eject_request)
            return (yield from self._handle_confirm(eject_request, ball_eject_process, incoming_ball_at_target))

    def _add_incoming_ball_to_target(self, eject_request: EjectRequest) -> IncomingBall:
        incoming_ball_at_target = IncomingBall()
        # we are the source of this ball
        incoming_ball_at_target.source = self.ball_device
        # there is no timeout
        incoming_ball_at_target.timeout_future = asyncio.Future(loop=self.machine.clock.loop)
        # we will wait on this future
        incoming_ball_at_target.confirm_future = eject_request.confirm_future
        eject_request.target.add_incoming_ball(incoming_ball_at_target)
        return incoming_ball_at_target

    def _remove_incoming_ball_at_target(self, eject_request: EjectRequest, incoming_ball_at_target: IncomingBall):
        eject_request.target.remove_incoming_ball(incoming_ball_at_target)
        incoming_ball_at_target.timeout_future.cancel()

    @asyncio.coroutine
    def _handle_confirm(self, eject_request: EjectRequest, ball_eject_process: EjectProcessCounter,
                        incoming_ball_at_target: IncomingBall) -> bool:
        # TODO: check double eject (two balls left)
        timeout = eject_request.eject_timeout
        self.debug_log("Wait for confirm with timeout %s", timeout)
        try:
            yield from Util.first([eject_request.wait_for_eject_confirm()], timeout=timeout,
                                  loop=self.machine.clock.loop, cancel_others=False)
        except asyncio.TimeoutError:
            self._state = "failed_confirm"
            self.debug_log("Got timeout before confirm")
            return (yield from self._handle_late_confirm_or_missing(eject_request, ball_eject_process,
                                                                    incoming_ball_at_target))
        else:
            if not eject_request.confirm_future.done():
                raise AssertionError("Future not done")
            if eject_request.confirm_future.cancelled():
                raise AssertionError("Eject failed but should not")
            # eject successful
            self.debug_log("Got eject confirm")
            ball_eject_process.eject_success()
            yield from self._handle_eject_success(eject_request.target)
            return True

    @asyncio.coroutine
    def _handle_late_confirm_or_missing(self, eject_request: EjectRequest, ball_eject_process: EjectProcessCounter,
                                        incoming_ball_at_target: IncomingBall) -> bool:
        ball_return_future = self.ball_device.ensure_future(ball_eject_process.wait_for_ball_return())
        eject_success_future = eject_request.wait_for_eject_confirm()
        timeout = 60    # TODO: make this dynamic

        # TODO: move this to a better location
        if not ball_return_future.done() and not ball_return_future.cancelled() and eject_request.target.is_playfield():
            # if target is playfield mark eject as confirmed
            self.debug_log("Confirming eject because target is playfield and ball did not return.")
            eject_request.confirm_future.set_result(True)
            eject_request.target.remove_incoming_ball(incoming_ball_at_target)

        # TODO: timeout
        try:
            event = yield from Util.first([ball_return_future, eject_success_future], timeout=timeout,
                                          loop=self.machine.clock.loop)
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
                ball_eject_process.eject_success()
                yield from self._handle_eject_success(eject_request.target)
                return True
            elif event == ball_return_future:
                # ball returned. eject failed
                ball_eject_process.ball_returned()
                return False
            else:
                raise AssertionError("Invalid state")

    @asyncio.coroutine
    def _handle_eject_success(self, eject_target):
        self.debug_log("Eject successful")
        yield from self.machine.events.post_async('balldevice_' + self.ball_device.name +
                                                  '_ball_eject_success',
                                                  balls=1,
                                                  target=eject_target)
        '''event: balldevice_(name)_ball_eject_success
        desc: One or more balls has successfully ejected from the device
            (name).
        args:
            balls: The number of balls that have successfully ejected.
            target: The target device that has received (or will be receiving)
                the ejected ball(s).
        '''
