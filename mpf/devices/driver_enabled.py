"""Contains the base class for driver-enabled devices."""
from mpf.core.system_wide_device import SystemWideDevice


class DriverEnabled(SystemWideDevice):
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

    def __init__(self, machine, name):
        super().__init__(machine, name)

        DriverEnabled.add_driver_enabled_device(self.hw_driver, self)

    def enable(self, **kwargs):
        del kwargs
        super().enable()
        for device in DriverEnabled.enable_driver_mappings[self.hw_driver]:
            device.enable_enable_driver()

    def enable_enable_driver(self):
        self.log.debug('Enabling')
        # print self, "enabling"

    def disable(self, **kwargs):
        del kwargs
        super().disable()
        # self.driver.disable()
        for device in DriverEnabled.enable_driver_mappings[self.hw_driver]:
            device.disable_enable_driver()

    def disable_enable_driver(self):
        self.log.debug('Disabling')

    def pulse(self, *args, **kwargs):
        del args
        del kwargs
        self.log.warning("Received request to pulse a driver-enabled device. "
                         "Ignoring...")
