class BallDeviceStateHandler:

    """Base class for ball device handler."""

    def __init__(self, ball_device):
        """Initialise handler."""
        self.ball_device = ball_device
        self.machine = ball_device.machine

    def debug_log(self, *args, **kwargs):
        """Debug log."""
        self.ball_device.debug_log(*args, **kwargs)