""" Contains the Driver parent class. """

from mpf.core.device import Device


class Driver(Device):
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

    def __init__(self, machine, name, config=None, validate=True):
        config['number_str'] = str(config['number']).upper()
        super().__init__(machine, name, config, platform_section='coils', validate=validate)

        self.time_last_changed = 0
        self.time_when_done = 0
        self.hw_driver, self.number = (
            self.platform.configure_driver(self.config))

    def validate_driver_settings(self, **kwargs):
        return self.hw_driver.validate_driver_settings(**kwargs)

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
        self.hw_driver.enable()

    def disable(self, **kwargs):
        """ Disables this driver """
        del kwargs
        self.log.debug("Disabling Driver")
        self.time_last_changed = self.machine.clock.get_time()
        self.time_when_done = self.time_last_changed
        self.machine.delay.remove(name='{}_timed_enable'.format(self.name))
        self.hw_driver.disable()

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

        # handle default case first
        if not milliseconds and not power:
            self.log.debug("Pulsing Driver. Using default pulse_ms.")
            ms_actual = self.hw_driver.pulse()
        else:
            if not milliseconds:
                raise AssertionError("Cannot use power without milliseconds")

            if power:
                milliseconds *= power
            else:
                power = 1.0

            if 0 < milliseconds <= 255:
                self.log.debug("Pulsing Driver. Overriding default pulse_ms with: "
                               "%sms (%s power)", milliseconds, power)
                ms_actual = self.hw_driver.pulse(milliseconds)
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

    def timed_enable(self, milliseconds, **kwargs):
        del kwargs
        self.pulse(milliseconds)
