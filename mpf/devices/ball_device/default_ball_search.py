"""Default ball search implementation for ejectors."""


class DefaultBallSearch:

    """Implement the default ball search behavior."""

    def ball_search(self, phase, iteration):
        """Run ball search."""
        del iteration
        if 'no-eject-on-ballsearch' in self.ball_device.config['tags']:
            return False
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
        # no action by default
        return False

    def _fire_coil_for_search(self, full_power):
        """Fire eject coil for search."""
        raise NotImplementedError()
