from mpf.core.device import Device


class ModeDevice(Device):
    def device_added_to_mode(self, mode, player):
        # Called when a device is created by a mode
        del mode
        del player
        self._initialize()

    def add_control_events_in_mode(self, mode):
        del mode
        # Called on mode start if this device has any control events in that mode
        # start mb if no enable_events are specified
        if "enable_events" in self.config and not self.config['enable_events']:
            self.enable()

    def remove_control_events_in_mode(self):
        pass

    def device_removed_from_mode(self):
        raise NotImplementedError(
            '{} does not have a device_removed_from_mode() method'.format(self.name))