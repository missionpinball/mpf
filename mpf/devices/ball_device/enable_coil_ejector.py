"""Enable/disable ejector."""
from mpf.core.delays import DelayManager
from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector


class EnableCoilEjector(BallDeviceEjector):

    """Enable a coil to eject one ball."""

    def __init__(self, ball_device):
        """Initialise ejector."""
        super().__init__(ball_device)
        self.delay = DelayManager(self.ball_device.machine.delayRegistry)

    def eject_one_ball(self, is_jammed, eject_try):
        """Enable eject coil."""
        del is_jammed
        # default pulse
        self.ball_device.debug_log("Enabling eject coil for %sms, Current balls: %s.",
                                   self.ball_device.config['eject_coil_enable_time'],
                                   self.ball_device.balls)

        self.ball_device.config['eject_coil'].enable()
        self.delay.reset(name="disable", callback=self._disable_coil,
                         ms=self.ball_device.config['eject_coil_enable_time'])

    def _disable_coil(self):
        """Disable the coil."""
        self.ball_device.config['eject_coil'].disable()

    def eject_all_balls(self):
        """Cannot eject all balls."""
        raise NotImplementedError()

    def ball_search(self, phase, iteration):
        """Run ball search."""
        del iteration
        if phase == 1:
            # round 1: only idle + no ball
            # only run ball search when the device is idle and contains no balls
            if self.ball_device.state == "idle" and self.ball_device.balls == 0:
                return self._fire_coil_for_search(True)
        elif phase == 2:
            # round 2: all devices except trough. only pulse
            if 'trough' not in self.ball_device.config['tags']:
                return self._fire_coil_for_search(False)
        else:
            # round 3: all devices except trough. release balls
            if 'trough' not in self.ball_device.config['tags']:
                return self._fire_coil_for_search(True)

    def _fire_coil_for_search(self, only_pulse):
        if only_pulse and self.ball_device.config['eject_coil_jam_pulse']:
            self.ball_device.config['eject_coil'].pulse()
        else:
            self.ball_device.config['eject_coil'].enable()
            self.delay.reset(name="disable", callback=self._disable_coil,
                             ms=self.ball_device.config['eject_coil_enable_time'])
        return True
