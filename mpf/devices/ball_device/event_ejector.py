"""Post an event to trigger an eject."""
import asyncio

from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector


class EventEjector(BallDeviceEjector):

    """Post an event to trigger an eject."""

    @asyncio.coroutine
    def eject_one_ball(self, is_jammed, eject_try):
        """Post event."""
        for event in self.config["events_when_eject_try"]:
            self.machine.events.post(event, is_jammed=is_jammed, eject_try=eject_try)

    @asyncio.coroutine
    def reorder_balls(self):
        """Reorder balls when jammed."""
        for event in self.config["events_when_reoder_balls"]:
            self.machine.events.post(event)

    def ball_search(self, phase, iteration):
        """Run ball search."""
        for event in self.config["events_when_ball_search"]:
            self.machine.events.post(event, phase=phase, iteration=iteration)

        # do not wait for this device
        return False
