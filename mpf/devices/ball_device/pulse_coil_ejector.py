"""Standard pulse ejector."""
from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector


class PulseCoilEjector(BallDeviceEjector):

    """Pulse a coil to eject one ball."""

    def eject_one_ball(self, is_jammed, eject_try):
        """Pulse eject coil."""
        if (eject_try <= 2 and
                self.ball_device.config['eject_coil_jam_pulse'] and
                is_jammed):
            # decreased pulse to only eject one ball
            self.ball_device.config['eject_coil'].pulse(
                self.ball_device.config['eject_coil_jam_pulse'])
        elif (eject_try >= self.ball_device.config['retries_before_increasing_pulse'] and
                self.ball_device.config['eject_coil_retry_pulse']):
            # increase pulse strength
            self.ball_device.config['eject_coil'].pulse(self.ball_device.config['eject_coil_retry_pulse'])
        else:
            # default pulse
            self.ball_device.config['eject_coil'].pulse()

        self.ball_device.debug_log("Firing eject coil. Current balls: %s.",
                                   self.ball_device.balls)

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
            # round 2: all devices except trough. small pulse
            if 'trough' not in self.ball_device.config['tags']:
                return self._fire_coil_for_search(False)
        else:
            # round 3: all devices except trough. normal pulse
            if 'trough' not in self.ball_device.config['tags']:
                return self._fire_coil_for_search(True)

    def _fire_coil_for_search(self, full_power):
        if not full_power and self.ball_device.config['eject_coil_jam_pulse']:
            self.ball_device.config['eject_coil'].pulse(self.ball_device.config['eject_coil_jam_pulse'])
        else:
            self.ball_device.config['eject_coil'].pulse()
        return True
