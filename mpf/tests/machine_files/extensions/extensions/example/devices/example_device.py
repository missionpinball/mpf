from mpf.core.device_monitor import DeviceMonitor
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor("multiplier")
class ExampleDevice(SystemWideDevice):

    config_section = 'example_devices'
    collection = 'example_devices'
    class_label = 'example_device'

    def __init__(self, machine, name):
        super().__init__(machine, name)
        self.multiplier = 0

    async def _initialize(self):
        await super()._initialize()
        self.multiplier = self.config['multiplier']
        self.info_log("Initialized %s with multiplier=%s", self.name, self.multiplier)
