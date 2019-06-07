"""Contains the Driver parent class."""
import asyncio
from typing import Optional

from mpf.core.delays import DelayManager
from mpf.core.events import event_handler
from mpf.core.machine import MachineController
from mpf.core.platform import DriverPlatform, DriverConfig
from mpf.core.system_wide_device import SystemWideDevice
from mpf.exceptions.DriverLimitsError import DriverLimitsError
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings


class Driver(SystemWideDevice):

    """Generic class that holds driver objects.

    A 'driver' is any device controlled from a driver board which is typically
    the high-voltage stuff like coils and flashers.

    This class exposes the methods you should use on these driver types of
    devices. Each platform module (i.e. P-ROC, FAST, etc.) subclasses this
    class to actually communicate with the physical hardware and perform the
    actions.

    Args: Same as the Device parent class
    """

    config_section = 'coils'
    collection = 'coils'
    class_label = 'coil'

    __slots__ = ["hw_driver", "delay", "platform", "__dict__"]

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialise driver."""
        self.hw_driver = None   # type: DriverPlatformInterface
        super().__init__(machine, name)
        self.delay = DelayManager(self.machine)
        self.platform = None                # type: DriverPlatform

    @classmethod
    def device_class_init(cls, machine: MachineController):
        """Register handler for duplicate coil number checks."""
        machine.events.add_handler("init_phase_4", cls._check_duplicate_coil_numbers, machine=machine)

    @staticmethod
    def _check_duplicate_coil_numbers(machine, **kwargs):
        del kwargs
        check_set = set()
        for coil in machine.coils:
            if not hasattr(coil, "hw_driver"):
                # skip dual wound and other special devices
                continue
            key = (coil.platform, coil.hw_driver.number)
            if key in check_set:
                raise AssertionError("Duplicate coil number {} for coil {}".format(coil.hw_driver.number, coil))

            check_set.add(key)

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Return the parsed and validated config.

        Args:
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide

        Returns: Validated config
        """
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        platform = self.machine.get_platform_sections('coils', getattr(config, "platform", None))
        config['platform_settings'] = platform.validate_coil_section(self, config.get('platform_settings', None))
        self._configure_device_logging(config)
        return config

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        self.platform = self.machine.get_platform_sections('coils', self.config['platform'])

        config = DriverConfig(
            default_pulse_ms=self.get_and_verify_pulse_ms(None),
            default_pulse_power=self.get_and_verify_pulse_power(None),
            default_hold_power=self.get_and_verify_hold_power(None),
            default_recycle=self.config['default_recycle'],
            max_pulse_ms=self.config['max_pulse_ms'],
            max_pulse_power=self.config['max_pulse_power'],
            max_hold_power=self.config['max_hold_power'])
        platform_settings = dict(self.config['platform_settings']) if self.config['platform_settings'] else dict()

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Driver must have a number.", 1)

        try:
            self.hw_driver = self.platform.configure_driver(config, self.config['number'], platform_settings)
        except AssertionError as e:
            raise AssertionError("Failed to configure driver {} in platform. See error above".format(self.name)) from e

    def get_and_verify_pulse_power(self, pulse_power: Optional[float]) -> float:
        """Return the pulse power to use.

        If pulse_power is None it will use the default_pulse_power. Additionally it will verify the limits.
        """
        if pulse_power is None:
            pulse_power = self.config['default_pulse_power'] if self.config['default_pulse_power'] is not None else 1.0

        if pulse_power and 0 > pulse_power > 1:
            raise AssertionError("Pulse power has to be between 0 and 1 but is {}".format(pulse_power))

        max_pulse_power = 0
        if self.config['max_pulse_power']:
            max_pulse_power = self.config['max_pulse_power']
        elif self.config['default_pulse_power']:
            max_pulse_power = self.config['default_pulse_power']

        if pulse_power > max_pulse_power:
            raise DriverLimitsError("Driver may {} not be pulsed with pulse_power {} because max_pulse_power is {}".
                                    format(self.name, pulse_power, max_pulse_power))
        return pulse_power

    def get_and_verify_hold_power(self, hold_power: Optional[float]) -> float:
        """Return the hold power to use.

        If hold_power is None it will use the default_hold_power. Additionally it will verify the limits.
        """
        if hold_power is None and self.config['default_hold_power']:
            hold_power = self.config['default_hold_power']

        if hold_power is None and self.config['max_hold_power']:
            hold_power = self.config['max_hold_power']

        if hold_power is None and self.config['allow_enable']:
            hold_power = 1.0

        if hold_power is None:
            hold_power = 0.0

        if hold_power and 0 > hold_power > 1:
            raise AssertionError("Hold_power has to be between 0 and 1 but is {}".format(hold_power))

        max_hold_power = 0      # type: float
        if self.config['max_hold_power']:
            max_hold_power = self.config['max_hold_power']
        elif self.config['allow_enable']:
            max_hold_power = 1.0
        elif self.config['default_hold_power']:
            max_hold_power = self.config['default_hold_power']

        if hold_power > max_hold_power:
            raise DriverLimitsError("Driver {} may not be enabled with hold_power {} because max_hold_power is {}".
                                    format(self.name, hold_power, max_hold_power))
        return hold_power

    def get_and_verify_pulse_ms(self, pulse_ms: Optional[int]) -> int:
        """Return and verify pulse_ms to use.

        If pulse_ms is None return the default.
        """
        if pulse_ms is None:
            if self.config['default_pulse_ms'] is not None:
                pulse_ms = self.config['default_pulse_ms']
            else:
                pulse_ms = self.machine.config['mpf']['default_pulse_ms']

        if not isinstance(pulse_ms, int):
            raise AssertionError("Wrong type {}".format(pulse_ms))

        if 0 > pulse_ms > self.platform.features['max_pulse']:
            raise AssertionError("Pulse_ms {} is not valid.".format(pulse_ms))

        if self.config['max_pulse_ms'] and pulse_ms > self.config['max_pulse_ms']:
            raise DriverLimitsError("Driver {} may not be pulsed with pulse_ms {} because max_pulse_ms is {}".
                                    format(self.name, pulse_ms, self.config['max_pulse_ms']))

        return pulse_ms

    @event_handler(2)
    def event_enable(self, pulse_ms: int = None, pulse_power: float = None, hold_power: float = None, **kwargs):
        """Event handler for control enable."""
        del kwargs
        self.enable(pulse_ms, pulse_power, hold_power)

    def enable(self, pulse_ms: int = None, pulse_power: float = None, hold_power: float = None):
        """Enable a driver by holding it 'on'.

        Args:
            pulse_ms: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            pulse_power: The pulse power. A float between 0.0 and 1.0.
            hold_power: The pulse power. A float between 0.0 and 1.0.

        If this driver is configured with a holdpatter, then this method will use
        that holdpatter to pwm pulse the driver.

        If not, then this method will just enable the driver. As a safety
        precaution, if you want to enable() this driver without pwm, then you
        have to add the following option to this driver in your machine
        configuration files:

        allow_enable: True
        """
        pulse_ms = self.get_and_verify_pulse_ms(pulse_ms)

        pulse_power = self.get_and_verify_pulse_power(pulse_power)
        hold_power = self.get_and_verify_hold_power(hold_power)

        if hold_power == 0.0:
            raise DriverLimitsError("Cannot enable driver with hold_power 0.0")

        self.info_log("Enabling Driver with power %s (pulse_ms %sms and pulse_power %s)", hold_power, pulse_ms,
                      pulse_power)
        self.hw_driver.enable(PulseSettings(power=pulse_power, duration=pulse_ms),
                              HoldSettings(power=hold_power))
        # inform bcp clients
        self.machine.bcp.interface.send_driver_event(action="enable", name=self.name, number=self.config['number'],
                                                     pulse_ms=pulse_ms, pulse_power=pulse_power, hold_power=hold_power)

    @event_handler(1)
    def event_disable(self, **kwargs):
        """Event handler for disable control event."""
        del kwargs
        self.disable()

    def disable(self):
        """Disable this driver."""
        self.info_log("Disabling Driver")
        self.machine.delay.remove(name='{}_timed_enable'.format(self.name))
        self.hw_driver.disable()
        # inform bcp clients
        self.machine.bcp.interface.send_driver_event(action="disable", name=self.name, number=self.config['number'])

    def _get_wait_ms(self, pulse_ms: int, max_wait_ms: Optional[int]) -> int:
        """Determine if this pulse should be delayed."""
        if max_wait_ms is None:
            self.config['psu'].notify_about_instant_pulse(pulse_ms=pulse_ms)
            return 0
        else:
            return self.config['psu'].get_wait_time_for_pulse(pulse_ms=pulse_ms, max_wait_ms=max_wait_ms)

    def _pulse_now(self, pulse_ms: int, pulse_power: float) -> None:
        """Pulse this driver now."""
        if 0 < pulse_ms <= self.platform.features['max_pulse']:
            self.info_log("Pulsing Driver for %sms (%s pulse_power)", pulse_ms, pulse_power)
            self.hw_driver.pulse(PulseSettings(power=pulse_power, duration=pulse_ms))
        else:
            self.info_log("Enabling Driver for %sms (%s pulse_power)", pulse_ms, pulse_power)
            self.delay.reset(name='timed_disable',
                             ms=pulse_ms,
                             callback=self.disable)
            self.hw_driver.enable(PulseSettings(power=pulse_power, duration=0),
                                  HoldSettings(power=pulse_power))
        # inform bcp clients
        self.machine.bcp.interface.send_driver_event(action="pulse", name=self.name, number=self.config['number'],
                                                     pulse_ms=pulse_ms, pulse_power=pulse_power)

    @event_handler(3)
    def event_pulse(self, pulse_ms: int = None, pulse_power: float = None, max_wait_ms: int = None, **kwargs) -> None:
        """Event handler for pulse control events."""
        del kwargs
        self.pulse(pulse_ms, pulse_power, max_wait_ms)

    def pulse(self, pulse_ms: int = None, pulse_power: float = None, max_wait_ms: int = None) -> int:
        """Pulse this driver.

        Args:
            pulse_ms: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            pulse_power: The pulse power. A float between 0.0 and 1.0.
        """
        pulse_ms = self.get_and_verify_pulse_ms(pulse_ms)
        pulse_power = self.get_and_verify_pulse_power(pulse_power)
        wait_ms = self._get_wait_ms(pulse_ms, max_wait_ms)

        if wait_ms > 0:
            self.debug_log("Delaying pulse by %sms pulse_ms: %sms (%s pulse_power)", wait_ms, pulse_ms, pulse_power)
            self.delay.add(wait_ms, self._pulse_now, pulse_ms=pulse_ms, pulse_power=pulse_power)
        else:
            self._pulse_now(pulse_ms, pulse_power)

        return wait_ms
