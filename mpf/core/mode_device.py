from mpf.core.device import Device


class ModeDevice(Device):
    def device_added_to_mode(self, mode, player):
        # Called when a device is created by a mode
        del mode
        del player
        self._initialize()

    def control_events_in_mode(self, mode):
        del mode
        # Called on mode start if this device has any control events in that mode
        # start mb if no enable_events are specified
        if "enable_events" in self.config and not self.config['enable_events']:
            self.enable()

    def remove(self):
        raise NotImplementedError(
            '{} does not have a remove() method'.format(self.name))