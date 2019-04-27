"""A digital output on either a light or driver platform."""
import asyncio
from functools import partial
from typing import Union, Tuple

from mpf.core.delays import DelayManager
from mpf.core.events import event_handler

from mpf.core.machine import MachineController
from mpf.core.platform import DriverConfig
from mpf.core.system_wide_device import SystemWideDevice
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

MYPY = False
if MYPY:    # noqa
    from mpf.core.platform import DriverPlatform, LightsPlatform
    from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface
    from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface


class DigitalOutput(SystemWideDevice):

    """A digital output on either a light or driver platform."""

    config_section = 'digital_outputs'
    collection = 'digital_outputs'
    class_label = 'digital_output'

    __slots__ = ["hw_driver", "platform", "type", "__dict__"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialise digital output."""
        self.hw_driver = None           # type: Union[DriverPlatformInterface, LightPlatformInterface]
        self.platform = None            # type: Union[DriverPlatform, LightsPlatform]
        self.type = None                # type: str
        super().__init__(machine, name)
        self.delay = DelayManager(self.machine)

    @asyncio.coroutine
    def _initialize(self):
        """Initialise the hardware driver for this digital output."""
        yield from super()._initialize()
        if self.config['type'] == "driver":
            self._initialize_driver()
        elif self.config['type'] == "light":
            self._initialize_light()
        else:
            raise AssertionError("Invalid type {}".format(self.config['type']))

    def _initialize_light(self):
        """Configure a light as digital output."""
        self.platform = self.machine.get_platform_sections('lights', self.config['platform'])
        self.type = "light"

        try:
            self.hw_driver = self.platform.configure_light(self.config['number'], self.config['light_subtype'], {})
        except AssertionError as e:
            raise AssertionError("Failed to configure light {} in platform. See error above".format(self.name)) from e

    def _initialize_driver(self):
        """Configure a driver as digital output."""
        self.platform = self.machine.get_platform_sections('coils', self.config['platform'])
        self.type = "driver"

        config = DriverConfig(
            default_pulse_ms=255,
            default_pulse_power=1.0,
            default_hold_power=1.0,
            default_recycle=False,
            max_pulse_ms=255,
            max_pulse_power=1.0,
            max_hold_power=1.0)

        try:
            self.hw_driver = self.platform.configure_driver(config, self.config['number'], {})
        except AssertionError as e:
            raise AssertionError("Failed to configure driver {} in platform. See error above".format(self.name)) from e

    @staticmethod
    def _get_state(max_fade_ms: int, state: bool) -> Tuple[float, int, bool]:
        """Return the current state without any fade."""
        del max_fade_ms
        if state:
            return 1.0, -1, True
        else:
            return 0.0, -1, True

    @event_handler(3)
    def event_pulse(self, pulse_ms, **kwargs):
        """Handle pulse control event."""
        del kwargs
        self.pulse(pulse_ms)

    def pulse(self, pulse_ms):
        """Pulse digital output."""
        if self.type == "driver":
            self.hw_driver.pulse(PulseSettings(power=1.0, duration=pulse_ms))
        elif self.type == "light":
            self.hw_driver.set_fade(partial(self._get_state, state=True))
            self.platform.light_sync()
            self.delay.reset(name='timed_disable',
                             ms=pulse_ms,
                             callback=self.disable)
        else:
            raise AssertionError("Invalid type {}".format(self.type))

    @event_handler(2)
    def event_enable(self, **kwargs):
        """Handle enable control event."""
        del kwargs
        self.enable()

    def enable(self):
        """Enable digital output."""
        if self.type == "driver":
            self.hw_driver.enable(PulseSettings(power=1.0, duration=0),
                                  HoldSettings(power=1.0))
        elif self.type == "light":
            self.hw_driver.set_fade(partial(self._get_state, state=True))
            self.platform.light_sync()
            self.delay.remove(name='timed_disable')
        else:
            raise AssertionError("Invalid type {}".format(self.type))

    @event_handler(1)
    def event_disable(self, **kwargs):
        """Handle disable control event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable digital output."""
        if self.type == "driver":
            self.hw_driver.disable()
        elif self.type == "light":
            self.hw_driver.set_fade(partial(self._get_state, state=False))
            self.platform.light_sync()
            self.delay.remove(name='timed_disable')
        else:
            raise AssertionError("Invalid type {}".format(self.type))
