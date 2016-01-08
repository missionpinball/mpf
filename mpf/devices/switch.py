""" Contains the Switch parent class. """

from mpf.system.device import Device
from mpf.system.timing import Timing


class Switch(Device):
    """ A switch in a pinball machine."""

    config_section = 'switches'
    collection = 'switches'
    class_label = 'switch'

    def __init__(self, machine, name, config, collection=None, validate=True):
        config['number_str'] = str(config['number']).upper()
        super(Switch, self).__init__(machine, name, config, collection,
                                     platform_section='switches',
                                     validate=validate)

        self.machine = machine
        self.name = name
        self.deactivation_events = set()
        self.activation_events = set()
        self.state = 0
        """ The logical state of a switch. 1 = active, 0 = inactive. This takes
        into consideration the NC or NO settings for the switch."""
        self.hw_state = 0
        """ The physical hardware state of the switch. 1 = active,
        0 = inactive. This is what the actual hardware is reporting and does
        not consider whether a switch is NC or NO."""

        self.invert = 0

        self.recycle_ticks = 0
        self.recycle_clear_tick = 0
        self.recycle_jitter_count = 0

        if self.config['type'].upper() == 'NC':
            self.invert = 1

        self.recycle_ticks = self.config['recycle_time']

        self.last_changed = None
        self.hw_timestamp = None

        self.log.debug("Creating '%s' with config: %s", name, self.config)

        self.hw_switch, self.number = (
            self.platform.configure_switch(self.config))
