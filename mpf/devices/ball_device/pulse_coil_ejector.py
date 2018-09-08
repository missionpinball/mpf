"""Standard pulse ejector."""
import asyncio

from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector
from mpf.exceptions.ConfigFileError import ConfigFileError


class PulseCoilEjector(BallDeviceEjector):

    """Pulse a coil to eject one ball."""

    __slots__ = []

    def __init__(self, config, ball_device, machine):
        """Initialise pulse coil ejector."""
        super().__init__(config, ball_device, machine)
        self._validate_config()

    def _validate_config(self):
        if not self.ball_device.config['eject_coil']:
            raise ConfigFileError("Pulse Coil Ejector needs an eject_coil.", 1,
                                  self.ball_device.log.name + "-pulse_ejector")
        #     if self.config['eject_coil_enable_time']:
        if self.ball_device.config['eject_coil_enable_time']:
            raise ConfigFileError("Pulse Coil Ejector does not support eject_coil_enable_time.", 2,
                                  self.ball_device.log.name + "-pulse_ejector")

    @asyncio.coroutine
    def eject_one_ball(self, is_jammed, eject_try):
        """Pulse eject coil."""
        max_wait_ms = self.ball_device.config['eject_coil_max_wait_ms']
        if (eject_try <= 2 and
                self.ball_device.config['eject_coil_jam_pulse'] and
                is_jammed):
            # decreased pulse to only eject one ball
            self.ball_device.config['eject_coil'].pulse(
                self.ball_device.config['eject_coil_jam_pulse'], max_wait_ms=max_wait_ms)
        elif (eject_try >= self.ball_device.config['retries_before_increasing_pulse'] and
                self.ball_device.config['eject_coil_retry_pulse']):
            # increase pulse strength
            self.ball_device.config['eject_coil'].pulse(self.ball_device.config['eject_coil_retry_pulse'],
                                                        max_wait_ms=max_wait_ms)
        else:
            # default pulse
            self.ball_device.config['eject_coil'].pulse(max_wait_ms=max_wait_ms)

        self.ball_device.debug_log("Firing eject coil. Current balls: %s.",
                                   self.ball_device.balls)

    @asyncio.coroutine
    def reorder_balls(self):
        """Reorder balls without ejecting."""
        if not self.ball_device.config['eject_coil_reorder_pulse']:
            self.ball_device.log.warning("Cannot reorder device because eject_coil_reorder_pulse is not configured")
            return

        max_wait_ms = self.ball_device.config['eject_coil_max_wait_ms']
        wait_ms = self.ball_device.config['eject_coil'].pulse(
            self.ball_device.config['eject_coil_reorder_pulse'],
            max_wait_ms=max_wait_ms)

        # wait for wait_ms + pulse_ms + 2s for sanity
        duration = wait_ms / 1000.0 + self.ball_device.config['eject_coil_reorder_pulse'] / 1000.0 + 2.0
        yield from asyncio.sleep(duration, loop=self.ball_device.machine.clock.loop)

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
        # no action by default
        return False

    def _fire_coil_for_search(self, full_power):
        if not full_power and self.ball_device.config['eject_coil_jam_pulse']:
            self.ball_device.config['eject_coil'].pulse(self.ball_device.config['eject_coil_jam_pulse'])
        else:
            self.ball_device.config['eject_coil'].pulse()
        return True
