"""A speedometer to measure the speed of a ball."""
from mpf.core.system_wide_device import SystemWideDevice


class Speedometer(SystemWideDevice):

    """A device which represents a tachometer."""

    config_section = 'speedometers'
    collection = 'speedometers'
    class_label = 'speedometer'

    __slots__ = ["time_start"]

    def __init__(self, machine, name):
        """initialize speedometer."""
        super().__init__(machine, name)
        self.time_start = None

    async def device_added_system_wide(self):
        """Register switch handlers on load."""
        await super().device_added_system_wide()

        self.machine.switch_controller.add_switch_handler_obj(
            self.config['start_switch'], self._handle_start_switch, 1)

        self.machine.switch_controller.add_switch_handler_obj(
            self.config['stop_switch'], self._handle_stop_switch, 1)

    def _handle_start_switch(self, **kwargs):
        del kwargs
        self.time_start = self.config['start_switch'].last_change

    def _handle_stop_switch(self, **kwargs):
        del kwargs
        if self.time_start is not None:
            delta = self.config['stop_switch'].last_change - self.time_start
            self.time_start = None
            print(delta)
            self.machine.events.post("{}_hit".format(self.name), delta = delta)
            # TODO: post event
