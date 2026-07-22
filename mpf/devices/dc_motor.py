"""A digital output on either a light or driver platform."""
from typing import Optional, TYPE_CHECKING

from mpf.core.delays import DelayManager
from mpf.core.events import event_handler

from mpf.core.machine import MachineController
from mpf.core.system_wide_device import SystemWideDevice

if TYPE_CHECKING:
    from mpf.core.platform import MotorPlatform    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.interfaces.motor_platform_interface import MotorPlatformInterface  # pylint: disable-msg=cyclic-import,unused-import; #noqa


class DCMotor(SystemWideDevice):

    """Represents a dc motor device in a pinball machine."""

    config_section = 'dc_motors'
    collection = 'dc_motors'
    class_label = 'dc_motor'

    __slots__ = ["hw_motor", "platform", "type", "__dict__"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialize dc motor."""
        self.hw_motor = None            # type: Optional[MotorPlatformInterface]
        self.platform = None            # type: Optional[MotorPlatform]
        super().__init__(machine, name)
        self.delay = DelayManager(self.machine)

    async def _initialize(self):
        await super()._initialize()
        self.platform = self.machine.get_platform_sections('motor_controllers', self.config['platform'])
        self.platform.assert_has_feature("motors")
        self.hw_motor = await self.platform.configure_dc_motor(self.config['number'], self.config['platform_settings'])
        for event, config in self.config['control_events'].items():
            if config.get('action') == 'stop':
                self.machine.events.add_handler(event, self.event_stop)
                continue
            if config.get('action') == 'pulse':
                self.machine.events.add_handler(event,
                                                self.event_pulse,
                                                power=config.get('power'),
                                                duration=config['duration'].evaluate({}))
                continue
            if config.get('action') == 'reverse_pulse':
                self.machine.events.add_handler(event,
                                                self.event_reverse_pulse,
                                                power=config.get('power'),
                                                duration=config['duration'].evaluate({}))
                continue
            # TODO: warn or crash on bad action selection?

    @event_handler(1)
    def event_pulse(self, duration=None, power=None, **kwargs):
        """Event handler for triggering a pulse."""
        del kwargs
        self.pulse(duration, power)

    def pulse(self, duration=None, power=None):
        """Pulse the dc motor for the given duration and power level."""
        if power is None:
            power = self.config['default_power']
        if not duration:
            raise AssertionError("DC Motor pulse called with no duration value")
        self.hw_motor.pulse(duration, power)

    @event_handler(2)
    def event_reverse_pulse(self, duration=None, power=None, **kwargs):
        """Event handler for triggering a reverse pulse."""
        del kwargs
        self.reverse_pulse(duration, power)

    def reverse_pulse(self, duration=None, power=None):
        """Pulse the dc motor for the given duration and power level in reverse."""
        if power is None:
            power = self.config['default_power']
        if not duration:
            raise AssertionError("DC Motor reverse pulse called with no duration value")
        self.hw_motor.reverse_pulse(duration, power)

    @event_handler(5)
    def event_stop(self, **kwargs):
        """Event handler for stopping the dc motor."""
        del kwargs
        self.stop()

    def stop(self):
        """Stop the dc motor."""
        self.hw_motor.stop()
