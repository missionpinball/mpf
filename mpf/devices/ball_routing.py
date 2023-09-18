"""Routes balls from one device to another when captured."""
from collections import defaultdict
from typing import List, Dict

from mpf.core.device_monitor import DeviceMonitor

from mpf.core.enable_disable_mixin import EnableDisableMixin
from mpf.core.events import EventHandlerKey

from mpf.devices.ball_device.ball_device import BallDevice

from mpf.core.mode import Mode
from mpf.core.mode_device import ModeDevice

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController   # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor("balls_routing")
class BallRouting(EnableDisableMixin, ModeDevice):

    """Route balls from one device to another when captured."""

    config_section = 'ball_routings'
    collection = 'ball_routings'
    class_label = 'ball_routing'

    __slots__ = ["_routing_queue", "_balls_at_target", "_handler"]

    def __init__(self, machine: "MachineController", name: str) -> None:
        """initialize device."""
        super().__init__(machine, name)
        self._routing_queue = defaultdict(int)      # type: Dict[BallDevice, int]
        self._balls_at_target = 0
        self._handler = []                          # type: List[EventHandlerKey]

    def _enable(self):
        """Enable routing."""
        for device in self.config['source_devices']:
            self._handler.append(
                self.machine.events.add_handler(
                    'balldevice_' + device.name + '_ball_enter',
                    self._claim_balls, device=device, priority=self.mode.priority))
            self._handler.append(
                self.machine.events.add_handler(
                    'balldevice_' + device.name + '_ball_entered',
                    self._route_ball, device=device, priority=self.mode.priority))

        self._handler.append(
            self.machine.events.add_handler(
                'balldevice_' + self.config['target_device'].name + '_ball_enter',
                self._add_ball, priority=self.mode.priority + 10000))
        self.debug_log("Enabling")

    def _claim_balls(self, device: BallDevice, unclaimed_balls, **kwargs):
        """Claim balls to route them to destination later."""
        del kwargs
        if not self._enabled:
            return {}
        # remember how many balls were captured
        self._routing_queue[device] += unclaimed_balls
        # claim all balls
        return {"unclaimed_balls": 0}

    def _route_ball(self, device: BallDevice, **kwargs):
        """Route balls to destination."""
        del kwargs
        self._balls_at_target += self._routing_queue[device]
        for _ in range(self._routing_queue[device]):
            device.eject(target=self.config['target_device'])

        self._routing_queue[device] = 0

    def _add_ball(self, unclaimed_balls, new_balls, **kwargs):
        """Mark balls as unclaimed at destination."""
        del kwargs
        claimed_balls = new_balls - unclaimed_balls
        if self._balls_at_target and claimed_balls:
            if claimed_balls <= self._balls_at_target:
                new_unexpected = unclaimed_balls + self._balls_at_target
                self.log.debug("Adding %s balls to target %s", new_unexpected, self.config['target_device'].name)
                self._balls_at_target = 0
                return {"unclaimed_balls": new_unexpected}

            self.log.debug("Adding %s balls to target %s", claimed_balls, self.config['target_device'].name)
            self._balls_at_target -= claimed_balls
            return {"unclaimed_balls": new_balls}

        return {}

    def _disable(self):
        """Disable routing."""
        self.debug_log("Disabling")
        self._enabled = False
        self.machine.events.remove_handlers_by_keys(self._handler)
        self._handler = []

    def device_removed_from_mode(self, mode: Mode) -> None:
        """Disable ball save when mode ends."""
        super().device_removed_from_mode(mode)
        self.debug_log("Removing")
        self.disable()
