"""A digital output on either a light or driver platform."""
from typing import Union, Optional

from mpf.core.delays import DelayManager
from mpf.core.events import event_handler

from mpf.core.machine import MachineController
from mpf.core.platform import DriverConfig, LightConfig, LightConfigColors
from mpf.core.system_wide_device import SystemWideDevice
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.core.platform import DriverPlatform, LightsPlatform    # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface  # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface    # pylint: disable-msg=cyclic-import,unused-import; # noqa

INVALID_TYPE_ERROR = "Invalid type {}"


class DigitalOutput(SystemWideDevice):

    """A digital output on either a light or driver platform."""

    config_section = 'digital_outputs'
    collection = 'digital_outputs'
    class_label = 'digital_output'

    __slots__ = ["hw_driver", "platform", "type", "__dict__"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """initialize digital output."""
        self.hw_driver = None           # type: Optional[Union[DriverPlatformInterface, LightPlatformInterface]]
        self.platform = None            # type: Optional[Union[DriverPlatform, LightsPlatform]]
        self.type = None                # type: Optional[str]
        super().__init__(machine, name)
        self.delay = DelayManager(self.machine)

    async def _initialize(self):
        """initialize the hardware driver for this digital output."""
        await super()._initialize()
        if self.config['type'] == "driver":
            self._initialize_driver()
        elif self.config['type'] == "light":
            self._initialize_light()
        else:
            raise AssertionError(INVALID_TYPE_ERROR.format(self.config['type']))

    def _initialize_light(self):
        """Configure a light as digital output."""
        self.platform = self.machine.get_platform_sections('lights', self.config['platform'])
        self.platform.assert_has_feature("lights")
        self.type = "light"

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Digital Output must have a number.", 1)

        config = LightConfig(
            name=self.name,
            color=LightConfigColors.NONE
        )

        try:
            self.hw_driver = self.platform.configure_light(self.config['number'], self.config['light_subtype'],
                                                           config, {})
        except AssertionError as e:
            raise AssertionError("Failed to configure light {} in platform. See error above".format(self.name)) from e

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Return the parsed and validated config.

        Args:
        ----
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide
            debug_prefix: Prefix to use when logging.

        Returns: Validated config
        """
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        if config['type'] == "driver":
            platform = self.machine.get_platform_sections('coils', getattr(config, "platform", None))
            platform.assert_has_feature("drivers")
            config['platform_settings'] = platform.validate_coil_section(self, config.get('platform_settings', None))
        elif config['type'] == "light":
            platform = self.machine.get_platform_sections('coils', getattr(config, "platform", None))
            platform.assert_has_feature("lights")
        else:
            raise AssertionError(INVALID_TYPE_ERROR.format(config['type']))
        return config

    def _initialize_driver(self):
        """Configure a driver as digital output."""
        self.platform = self.machine.get_platform_sections('coils', self.config['platform'])
        self.platform.assert_has_feature("drivers")
        self.type = "driver"

        config = DriverConfig(
            name=self.name,
            default_pulse_ms=255,
            default_pulse_power=1.0,
            default_timed_enable_ms=None,
            default_hold_power=1.0,
            default_recycle=False,
            max_pulse_ms=255,
            max_pulse_power=1.0,
            max_hold_power=1.0)

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Digital Output must have a number.", 2)

        try:
            self.hw_driver = self.platform.configure_driver(config, self.config['number'],
                                                            self.config['platform_settings'])
        except AssertionError as e:
            raise AssertionError("Failed to configure driver {} in platform. See error above".format(self.name)) from e

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
            self.hw_driver.set_fade(1.0, -1, 1.0, -1)
            self.platform.light_sync()
            self.delay.reset(name='timed_disable',
                             ms=pulse_ms,
                             callback=self.disable)
        else:
            raise AssertionError(INVALID_TYPE_ERROR.format(self.type))

    @event_handler(2)
    def event_enable(self, **kwargs):
        """Handle enable control event."""
        del kwargs
        self.enable()

    def enable(self):
        """Enable digital output."""
        if self.type == "driver":
            self.hw_driver.enable(PulseSettings(power=1.0, duration=0),
                                  HoldSettings(power=1.0, duration=None))
        elif self.type == "light":
            self.hw_driver.set_fade(1.0, -1, 1.0, -1)
            self.platform.light_sync()
            self.delay.remove(name='timed_disable')
        else:
            raise AssertionError(INVALID_TYPE_ERROR.format(self.type))

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
            self.hw_driver.set_fade(0.0, -1, 0.0, -1)
            self.platform.light_sync()
            self.delay.remove(name='timed_disable')
        else:
            raise AssertionError(INVALID_TYPE_ERROR.format(self.type))
