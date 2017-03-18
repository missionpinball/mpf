"""Contains the Driver parent class."""
import copy

from typing import Any, Dict

from mpf.core.machine import MachineController
from mpf.core.platform import DriverPlatform
from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.switch import Switch
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

    def __init__(self, machine: MachineController, name: str) -> None:
        """Initialise driver."""
        self.hw_driver = None   # type: DriverPlatformInterface
        super().__init__(machine, name)

        self.time_last_changed = -1
        self.time_when_done = -1
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

    def validate_and_parse_config(self, config: dict, is_mode_config: bool) -> dict:
        """Return the parsed and validated config.

        Args:
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide

        Returns: Validated config
        """
        del is_mode_config
        platform = self.machine.get_platform_sections('coils', getattr(config, "platform", None))
        platform.validate_coil_section(self, config)
        self._configure_device_logging(config)
        return config

    def _initialize(self):
        self.platform = self.machine.get_platform_sections('coils', self.config['platform'])

        config = dict(self.config)
        if 'psu' in config:
            del config['psu']
        self.hw_driver = self.platform.configure_driver(config)

    def get_and_verify_pulse_power(self, pulse_power: float) -> float:
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
            raise AssertionError("Driver may {} not be pulsed with pulse_power {} because max_pulse_power is {}".
                                 format(self.name, pulse_power, max_pulse_power))
        return pulse_power

    def get_and_verify_hold_power(self, hold_power: float) -> float:
        """Return the hold power to use.

        If hold_power is None it will use the default_hold_power. Additionally it will verify the limits.
        """
        if hold_power is None:
            hold_power = self.config['default_hold_power'] if self.config['default_hold_power'] is not None else 1.0

        if hold_power and 0 > hold_power > 1:
            raise AssertionError("Hold_power has to be between 0 and 1 but is {}".format(hold_power))

        max_hold_power = 0
        if self.config['max_hold_power']:
            max_hold_power = self.config['max_hold_power']
        elif self.config['default_hold_power']:
            max_hold_power = self.config['default_hold_power']

        if hold_power > max_hold_power:
            raise AssertionError("Driver {} may not be enabled with hold_power {} because max_hold_power is {}".
                                 format(self.name, hold_power, max_hold_power))
        return hold_power

    def get_and_verify_pulse_ms(self, pulse_ms: int) -> int:
        """Return and verify pulse_ms to use.

        If pulse_ms is None return the default.
        """
        if not pulse_ms:
            if self.config['default_pulse_ms']:
                pulse_ms = self.config['default_pulse_ms']
            else:
                pulse_ms = self.machine.config['mpf']['default_pulse_ms']

        if 0 > pulse_ms > self.platform.features['max_pulse']:
            raise AssertionError("Pulse_ms {} is not valid.".format(pulse_ms))

        return pulse_ms

    def enable(self, pulse_ms: int=None, pulse_power: float=None, hold_power: float=None, **kwargs):
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
        del kwargs

        pulse_ms = self.get_and_verify_pulse_ms(pulse_ms)

        pulse_power = self.get_and_verify_pulse_power(pulse_power)
        hold_power = self.get_and_verify_hold_power(hold_power)

        self.time_when_done = -1
        self.time_last_changed = self.machine.clock.get_time()
        self.debug_log("Enabling Driver")
        self.hw_driver.enable(PulseSettings(power=pulse_power, duration=pulse_ms),
                              HoldSettings(power=hold_power))

    def disable(self, **kwargs):
        """Disable this driver."""
        del kwargs
        self.debug_log("Disabling Driver")
        self.time_last_changed = self.machine.clock.get_time()
        self.time_when_done = self.time_last_changed
        self.machine.delay.remove(name='{}_timed_enable'.format(self.name))
        self.hw_driver.disable()

    def pulse(self, pulse_ms: int=None, pulse_power: float=None, **kwargs):
        """Pulse this driver.

        Args:
            pulse_ms: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            pulse_power: The pulse power. A float between 0.0 and 1.0.
        """
        del kwargs

        pulse_ms = self.get_and_verify_pulse_ms(pulse_ms)

        pulse_power = self.get_and_verify_pulse_power(pulse_power)

        if 0 < pulse_ms <= self.platform.features['max_pulse']:
            self.debug_log("Pulsing Driver. %sms (%s pulse_power)", pulse_ms, pulse_power)
            self.hw_driver.pulse(PulseSettings(power=pulse_power, duration=pulse_ms))
        else:
            self.debug_log("Enabling Driver for %sms (%s pulse_power)", pulse_ms, pulse_power)
            self.machine.delay.reset(name='{}_timed_enable'.format(self.name),
                                     ms=pulse_ms,
                                     callback=self.disable)
            self.hw_driver.enable(PulseSettings(power=pulse_power, duration=0),
                                  HoldSettings(power=pulse_power))

        # only needed for score reels
        # self.time_last_changed = self.machine.clock.get_time()
        self.time_when_done = self.time_last_changed + int(pulse_ms / 1000.0)


class ConfiguredHwDriver:

    """A (re-)configured Hw driver."""

    def __init__(self, hw_driver: DriverPlatformInterface, config_overwrite: dict) -> None:
        """Initialise configured hw driver."""
        self.hw_driver = hw_driver
        self.config = copy.deepcopy(self.hw_driver.config)
        for name, item in config_overwrite.items():
            if item is not None:
                self.config[name] = item

    def __eq__(self, other):
        """Compare two configured hw drivers."""
        return self.hw_driver == other.hw_driver and self.config == other.config

    def __hash__(self):
        """Return id of hw_driver and config for comparison."""
        return id((self.hw_driver, self.config))


class ReconfiguredDriver(Driver):

    """A reconfigured driver."""

    # pylint: disable-msg=super-init-not-called
    def __init__(self, driver, config_overwrite):
        """Reconfigure a driver.

        No call to super init because we do not want to initialise the driver again.
        """
        self._driver = driver
        self._config_overwrite = driver.platform.validate_coil_overwrite_section(driver, config_overwrite)
        self._configured_driver = None

    def __getattr__(self, item):
        """Return parent attributes."""
        return getattr(self._driver, item)

    def get_configured_driver(self):
        """Return configured hw driver."""
        if not self._configured_driver:
            self._configured_driver = ConfiguredHwDriver(self.hw_driver, self._config_overwrite)
        return self._configured_driver

    @property
    def config(self) -> Dict[str, Any]:
        """Return the merged config."""
        config = dict(self._driver.config)
        for name, item in self._config_overwrite.items():
            if item is not None:
                config[name] = item

        return config
