""" Contains the Switch parent class. """

from mpf.core.system_wide_device import SystemWideDevice


class Switch(SystemWideDevice):
    """ A switch in a pinball machine."""

    config_section = 'switches'
    collection = 'switches'
    class_label = 'switch'

    def __init__(self, machine, name):
        super().__init__(machine, name)

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

        self.recycle_secs = 0
        self.recycle_clear_time = 0
        self.recycle_jitter_count = 0

        self.last_changed = None
        self.hw_timestamp = None

        # register switch so other devices can add handlers to it
        self.machine.switch_controller.register_switch(name)

    def prepare_config(self, config, is_mode_config):
        del is_mode_config
        config['number_str'] = str(config['number']).upper()
        return config

    def _initialize(self):
        self.load_platform_section('switches')

        if self.config['type'].upper() == 'NC':
            self.invert = 1

        self.recycle_secs = self.config['recycle_time']

        self.hw_switch, self.number = (
            self.platform.configure_switch(self.config))
