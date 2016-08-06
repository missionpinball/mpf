"""Contains the Driver parent class."""
import copy

from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.switch import Switch
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface


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

    def __init__(self, machine, name):
        """Initialise driver."""
        self.hw_driver = None
        super().__init__(machine, name)

        self.time_last_changed = -1
        self.time_when_done = -1
        self._configured_driver = None

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
        return config

    def _initialize(self):
        self.load_platform_section('coils')

        self.hw_driver = self.platform.configure_driver(self.config)

    def enable(self, **kwargs):
        """Enable a driver by holding it 'on'.

        If this driver is configured with a holdpatter, then this method will use
        that holdpatter to pwm pulse the driver.

        If not, then this method will just enable the driver. As a safety
        precaution, if you want to enable() this driver without pwm, then you
        have to add the following option to this driver in your machine
        configuration files:

        allow_enable: True
        """
        del kwargs

        self.time_when_done = -1
        self.time_last_changed = self.machine.clock.get_time()
        self.log.debug("Enabling Driver")
        self.hw_driver.enable(self.get_configured_driver())

    def disable(self, **kwargs):
        """Disable this driver."""
        del kwargs
        self.log.debug("Disabling Driver")
        self.time_last_changed = self.machine.clock.get_time()
        self.time_when_done = self.time_last_changed
        self.machine.delay.remove(name='{}_timed_enable'.format(self.name))
        self.hw_driver.disable(self.get_configured_driver())

    def get_configured_driver(self):
        """Return a configured hw driver."""
        if not self._configured_driver:
            self._configured_driver = ConfiguredHwDriver(self.hw_driver, {})
        return self._configured_driver

    def pulse(self, milliseconds: int=None, power: float=None, **kwargs):
        """Pulse this driver.

        Args:
            milliseconds: The number of milliseconds the driver should be
                enabled for. If no value is provided, the driver will be
                enabled for the value specified in the config dictionary.
            power: A multiplier that will be applied to the default pulse time,
                typically a float between 0.0 and 1.0. (Note this is can only be used
                if milliseconds is also specified.)
        """
        del kwargs

        if not milliseconds:
            if self.config['pulse_ms']:
                milliseconds = self.config['pulse_ms']
            else:
                milliseconds = self.machine.config['mpf']['default_pulse_ms']

        if power:
            milliseconds = int(power * milliseconds)
        else:
            power = 1.0

        if 0 < milliseconds <= self.platform.features['max_pulse']:
            self.log.debug("Pulsing Driver. %sms (%s power)", milliseconds, power)
            ms_actual = self.hw_driver.pulse(self.get_configured_driver(), milliseconds)
        else:
            self.log.debug("Enabling Driver for %sms (%s power)", milliseconds, power)
            self.machine.delay.reset(name='{}_timed_enable'.format(self.name),
                                     ms=milliseconds,
                                     callback=self.disable)
            self.enable()
            self.time_when_done = self.time_last_changed + (
                milliseconds / 1000.0)
            ms_actual = milliseconds

        if ms_actual != -1:
            self.time_when_done = self.time_last_changed + (ms_actual / 1000.0)
        else:
            self.time_when_done = -1

    def _check_platform(self, switch: Switch):
        # TODO: handle stuff in software if platforms differ
        if self.platform != switch.platform:
            raise AssertionError("Switch and Coil have to use the same platform")

    def set_pulse_on_hit_and_release_rule(self, enable_switch: Switch):
        """Add pulse on hit and relase rule to driver.

        Pulse a driver but cancel pulse when switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
        """
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_and_release_rule(enable_switch.get_configured_switch(),
                                                        self.get_configured_driver())

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: Switch):
        """Add pulse on hit and enable and relase rule to driver.

        Pulse and enable a driver. Cancel pulse and enable if switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
        """
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_and_enable_and_release_rule(enable_switch.get_configured_switch(),
                                                                   self.get_configured_driver())

    def set_pulse_on_hit_rule(self, enable_switch: Switch):
        """Add pulse on hit rule to driver.

        Alway do the full pulse. Even when the switch is released.

        Args:
            enable_switch: Switch which triggers the rule.
        """
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_rule(enable_switch.get_configured_switch(), self.get_configured_driver())

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: Switch, disable_switch: Switch):
        """Add pulse on hit and enable and release and disable rule to driver.

        Pulse and then enable driver. Cancel pulse and enable when switch is released or a disable switch is hit.

        Args:
            enable_switch: Switch which triggers the rule.
            disable_switch: Switch which disables the rule.
        """
        self._check_platform(enable_switch)
        self._check_platform(disable_switch)

        self.platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule(
            enable_switch.get_configured_switch(),
            disable_switch.get_configured_switch(),
            self.get_configured_driver()
        )

    def clear_hw_rule(self, switch: Switch):
        """Clear all rules for switch and this driver.

        Args:
            switch: Switch to clear on this driver.
        """
        self.platform.clear_hw_rule(switch.get_configured_switch(), self.get_configured_driver())


class ConfiguredHwDriver:

    """A (re-)configured Hw driver."""

    def __init__(self, hw_driver: DriverPlatformInterface, config_overwrite: dict):
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
    def config(self) -> dict:
        """Return the merged config."""
        config = copy.deepcopy(self._driver.config)
        for name, item in self._config_overwrite.items():
            if item is not None:
                config[name] = item

        return config
