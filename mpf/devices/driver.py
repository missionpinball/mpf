""" Contains the Driver parent class. """
import copy

from mpf.core.system_wide_device import SystemWideDevice


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
        self.hw_driver = None
        super().__init__(machine, name)

        self.time_last_changed = 0
        self.time_when_done = 0
        self._configured_driver = None

    def validate_and_parse_config(self, config, is_mode_config):
        platform = self.machine.get_platform_sections('coils', getattr(config, "platform", None))
        platform.validate_coil_section(self, config)
        return config

    def _initialize(self):
        self.load_platform_section('coils')

        self.hw_driver = self.platform.configure_driver(self.config)

    def enable(self, **kwargs):
        """Enables a driver by holding it 'on'.

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
        """ Disables this driver """
        del kwargs
        self.log.debug("Disabling Driver")
        self.time_last_changed = self.machine.clock.get_time()
        self.time_when_done = self.time_last_changed
        self.machine.delay.remove(name='{}_timed_enable'.format(self.name))
        self.hw_driver.disable(self.get_configured_driver())

    def get_configured_driver(self):
        if not self._configured_driver:
            self._configured_driver = ConfiguredHwDriver(self.hw_driver, {})
        return self._configured_driver

    def pulse(self, milliseconds=None, power=None, **kwargs):
        """ Pulses this driver.

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

    def _check_platform(self, switch):
        # TODO: handle stuff in software if platforms differ
        if self.platform != switch.platform:
            raise AssertionError("Switch and Coil have to use the same platform")

    def set_pulse_on_hit_and_release_rule(self, enable_switch):
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_and_release_rule(enable_switch.get_configured_switch(),
                                                        self.get_configured_driver())

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch):
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_and_enable_and_release_rule(enable_switch.get_configured_switch(),
                                                                   self.get_configured_driver())

    def set_pulse_on_hit_rule(self, enable_switch):
        self._check_platform(enable_switch)

        self.platform.set_pulse_on_hit_rule(enable_switch.get_configured_switch(), self.get_configured_driver())

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch):
        self._check_platform(enable_switch)
        self._check_platform(disable_switch)

        self.platform.set_pulse_on_hit_and_enable_and_release_and_disable_rule(
            enable_switch.get_configured_switch(),
            disable_switch.get_configured_switch(),
            self.get_configured_driver()
        )

    def clear_hw_rule(self, switch):
        self.platform.clear_hw_rule(switch.get_configured_switch(), self.get_configured_driver())


class ConfiguredHwDriver:
    def __init__(self, hw_driver, config_overwrite):
        self.hw_driver = hw_driver
        self.config = copy.deepcopy(self.hw_driver.config)
        for name, item in config_overwrite.items():
            if item is not None:
                self.config[name] = item

    def __eq__(self, other):
        return self.hw_driver == other.hw_driver and self.config == other.config

    def __hash__(self):
        return id((self.hw_driver, self.config))


class ReconfiguredDriver(Driver):
    def __init__(self, driver, config_overwrite):
        # no call to super init
        self._driver = driver
        self._config_overwrite = driver.platform.validate_coil_overwrite_section(driver, config_overwrite)
        self._configured_driver = None

    def __getattr__(self, item):
        return getattr(self._driver, item)

    def get_configured_driver(self):
        if not self._configured_driver:
            self._configured_driver = ConfiguredHwDriver(self.hw_driver, self._config_overwrite)
        return self._configured_driver

    @property
    def config(self):
        config = copy.deepcopy(self._driver.config)
        for name, item in self._config_overwrite.items():
            if item is not None:
                config[name] = item

        return config
