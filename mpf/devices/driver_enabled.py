"""Contains the base class for driver-enabled devices."""

from mpf.devices.driver import Driver


class DriverEnabled(Driver):
    """Represents a "driver-enabled" device in a pinball machine.
    """
    config_section = 'driver_enabled'
    collection = 'driver_enabled'
    class_label = 'driver_enabled'

    enable_driver_mappings = dict()  # k: driver, v: DriverEnabled device list

    @classmethod
    def add_driver_enabled_device(cls, driver, device):
        if driver not in DriverEnabled.enable_driver_mappings:
            DriverEnabled.enable_driver_mappings[driver] = set()

        DriverEnabled.enable_driver_mappings[driver].add(device)

    def __init__(self, machine, name, config, collection=None, validate=True):
        super().__init__(machine, name, config, collection,
                         validate=validate)

        DriverEnabled.add_driver_enabled_device(self.hw_driver, self)

    def enable(self, **kwargs):
        super().enable()
        for device in DriverEnabled.enable_driver_mappings[self.hw_driver]:
            device._enable()

    def _enable(self):
        pass
        self.log.debug('Enabling')
        # print self, "enabling"

    def disable(self, **kwargs):
        super().disable()
        # self.driver.disable()
        for device in DriverEnabled.enable_driver_mappings[self.hw_driver]:
            device._disable()

    def _disable(self):
        pass
        self.log.debug('Disabling')
        # print self, "disabling"

    def pulse(self, *args, **kwargs):
        self.log.warning("Received request to pulse a driver-enabled device. "
                         "Ignoring...")

    def timed_enable(self, *args, **kwargs):
        self.log.warning("Received request to timed-enable a driver-enabled "
                         "device. Ignoring...")
