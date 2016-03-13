from mpf.core.device import Device


class ModeDevice(Device):
    def device_added_to_mode(self, mode, player):
        # Called when a device is created by a mode
        del mode
        del player
        self._initialize()

    def control_events_in_mode(self, mode):
        # Called on mode start if this device has any control events in that mode
        pass

    def remove(self):
        raise NotImplementedError(
            '{} does not have a remove() method'.format(self.name))