"""Baseclass for ball device ejectors."""


class BallDeviceEjector:

    """Ejector for a ball device.

    It has to implement at least one of eject_one_ball or eject_all_balls.
    """

    def __init__(self, ball_device):
        """Initialise ejector."""
        self.ball_device = ball_device

    # TODO: make this coroutine
    def eject_one_ball(self, is_jammed, eject_try):
        """Eject one ball."""
        raise NotImplementedError()

    # TODO: make this coroutine
    def eject_all_balls(self):
        """Eject all balls."""
        raise NotImplementedError()

    def ball_search(self, phase, iteration):
        """Search ball in device."""
        raise NotImplementedError()
