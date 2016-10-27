"""Handles outgoing balls."""
import asyncio

from mpf.core.utility_functions import Util
from mpf.devices.ball_device.ball_device_state_handler import BallDeviceStateHandler


class OutgoingBallsHandler(BallDeviceStateHandler):

    """Handles all outgoing balls."""

    def __init__(self, ball_device):
        super().__init__(ball_device)
        self._eject_queue = asyncio.Queue(loop=self.machine.clock.loop)

    @asyncio.coroutine
    def _handle_ejects(self):
        """Wait for eject queue."""
        while True:
            eject_queue_future = self.ball_device.ensure_future(self._eject_queue.get())
            eject_request = yield from eject_queue_future

            self.debug_log("Got eject request")

            yield from self._ejecting(eject_request)

    @asyncio.coroutine
    def _ejecting(self, eject_request):
        """Perform main eject loop."""
        # TODO: handle unexpected mechanical eject
        eject_try = 0
        while True:
            # wait until we have a ball (might be instant)
            yield from self.ball_device.ball_count_handler.wait_for_ball()
            # inform targets about the eject (can delay the eject)
            yield from self._prepare_eject(eject_request)
            # check if we still have a ball
            ball_count = yield from self.ball_device.ball_count_handler.get_ball_count()
            if ball_count == 0:
                # abort the eject because ball was lost in the meantime
                # TODO: might be mechanical eject
                yield from self._abort_eject(eject_request, eject_try)
                # try again
                continue

            result = yield from self._eject_ball(eject_request, eject_try)
            if result:
                # eject is done. return to main loop
                return

            yield from self._failed_eject(eject_request, eject_try)
            eject_try += 1

            if eject_request['max_tries'] and eject_try > eject_request['max_tries']:
                # stop device
                self.ball_device.stop()
                # TODO: inform machine about broken device
                return

    @asyncio.coroutine
    def _prepare_eject(self, eject_request):
        pass

    @asyncio.coroutine
    def _abort_eject(self, eject_request):
        pass

    @asyncio.coroutine
    def _failed_eject(self, eject_request):
        pass

    @asyncio.coroutine
    def _eject_ball(self, eject_request, eject_try) -> bool:
        # inform the counter that we are ejecting now
        ball_eject_process = self.machine.ball_count_handler.start_eject()
        # eject the ball
        yield from self.ball_device.ejector.eject_one_ball(ball_eject_process.is_jammed(), eject_try)
        # wait until the ball has left
        try:
            yield from ball_eject_process.wait_for_ball_left(eject_request['eject_timeout'])
        except asyncio.TimeoutError:
            # timeout. ball did not leave. failed
            ball_eject_process.cancel()
            return False
        else:
            return (yield from self._handle_confirm(eject_request, ball_eject_process))

    @asyncio.coroutine
    def _handle_confirm(self, eject_request, ball_eject_process) -> bool:
        # TODO: check double eject
        try:
            # TODO: timeout
            yield from eject_request.wait_for_eject_confirm(ball_eject_process)
        except asyncio.TimeoutError:
            # ball did not get confirmed
            if ball_eject_process.is_ball_returned():
                # ball returned. eject failed
                return False
            return (yield from self._handle_late_confirm_or_missing(eject_request, ball_eject_process))
        else:
            # eject successful
            yield from ball_eject_process.eject_done()
            return True

    @asyncio.coroutine
    def _handle_late_confirm_or_missing(self, eject_request, ball_eject_process) -> bool:
        ball_return_future = ball_eject_process.wait_for_ball_return()
        eject_success_future = eject_request.wait_for_eject_confirm(ball_eject_process)

        # TODO: timeout
        try:
            event = yield from Util.first([ball_return_future, eject_success_future], loop=self.machine.clock.loop)
        except asyncio.TimeoutError:
            # handle lost ball
            raise AssertionError("handle lost ball")
        else:
            if event == eject_success_future:
                # we eventually got eject success
                return True
            elif event == ball_return_future:
                # ball returned. eject failed
                return False
            else:
                raise AssertionError("Invalid state")
