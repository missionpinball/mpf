"""Standard pulse ejector."""
from typing import List

import asyncio

from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector
from mpf.devices.ball_device.default_ball_search import DefaultBallSearch
from mpf.exceptions.config_file_error import ConfigFileError


class PulseCoilEjector(DefaultBallSearch, BallDeviceEjector):

    """Pulse a coil to eject one ball."""

    __slots__ = []  # type: List[str]

    def __init__(self, config, ball_device, machine):
        """Initialise pulse coil ejector."""
        for option in ["eject_coil", "eject_coil_jam_pulse", "eject_coil_retry_pulse", "eject_coil_reorder_pulse",
                       "eject_coil_max_wait_ms", "retries_before_increasing_pulse"]:
            if option not in config and option in ball_device.config:
                config[option] = ball_device.config[option]

        super().__init__(config, ball_device, machine)

        self.config = self.machine.config_validator.validate_config("ball_device_ejector_pulse", self.config)

        # prevent conflicting options
        if "eject_coil_enable_time" in self.ball_device.config and self.ball_device.config['eject_coil_enable_time']:
            raise ConfigFileError("Pulse Coil Ejector does not support eject_coil_enable_time.", 2,
                                  self.ball_device.log.name + "-pulse_ejector")

    @staticmethod
    def _get_pulse_setting_for_ball_count(pulse_setting, balls_in_device):
        """Select the setting depending on the ball count in the device."""
        if len(pulse_setting) >= balls_in_device:
            return pulse_setting[balls_in_device - 1]

        # default -> last setting
        return pulse_setting[-1]

    async def eject_one_ball(self, is_jammed, eject_try, balls_in_device):
        """Pulse eject coil."""
        max_wait_ms = self.config['eject_coil_max_wait_ms']
        if eject_try <= 2 and self.config['eject_coil_jam_pulse'] and is_jammed:
            # jammed -> different pulse settings to only eject one ball
            self.config['eject_coil'].pulse(
                self._get_pulse_setting_for_ball_count(self.config['eject_coil_jam_pulse'], balls_in_device),
                max_wait_ms=max_wait_ms)
        elif eject_try >= self.config['retries_before_increasing_pulse'] and self.config['eject_coil_retry_pulse']:
            # multiple failed ejects -> increase pulse strength
            self.config['eject_coil'].pulse(
                self._get_pulse_setting_for_ball_count(self.config['eject_coil_retry_pulse'], balls_in_device),
                max_wait_ms=max_wait_ms)
        elif self.config["eject_times"]:
            # use pulse_times parameter
            self.config['eject_coil'].pulse(
                self._get_pulse_setting_for_ball_count(self.config['eject_times'], balls_in_device),
                max_wait_ms=max_wait_ms)
        else:
            # default pulse
            self.config['eject_coil'].pulse(max_wait_ms=max_wait_ms)

        self.ball_device.debug_log("Firing eject coil. Current balls: %s.", self.ball_device.balls)

    async def reorder_balls(self):
        """Reorder balls without ejecting."""
        if not self.config['eject_coil_reorder_pulse']:
            self.ball_device.log.warning("Cannot reorder device because eject_coil_reorder_pulse is not configured")
            return

        max_wait_ms = self.config['eject_coil_max_wait_ms']
        wait_ms = self.config['eject_coil'].pulse(self.config['eject_coil_reorder_pulse'], max_wait_ms=max_wait_ms)

        # wait for wait_ms + pulse_ms + 2s for sanity
        duration = wait_ms / 1000.0 + self.config['eject_coil_reorder_pulse'] / 1000.0 + 2.0
        await asyncio.sleep(duration)

    def _fire_coil_for_search(self, full_power):
        if not full_power and self.config['eject_coil_jam_pulse']:
            self.config['eject_coil'].pulse(self.config['eject_coil_jam_pulse'][0])
        else:
            self.config['eject_coil'].pulse()
        return True
