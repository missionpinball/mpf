from mpf.core.device import Device


class SystemWideDevice(Device):
    def device_added_system_wide(self):
        # Called when a device is added system wide
        self._initialize()