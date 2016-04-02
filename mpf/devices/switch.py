""" Contains the Switch parent class. """
import copy

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

    def validate_and_parse_config(self, config, is_mode_config):
        platform = self.machine.get_platform_sections('switches', getattr(config, "platform", None))
        if platform.get_switch_config_section():
            self.machine.config_validator.validate_config(
                self.config_section, config, self.name, base_spec=platform.get_switch_config_section())
        else:
            super().validate_and_parse_config(config, is_mode_config)

        return config

    def _initialize(self):
        self.load_platform_section('switches')

        if self.config['type'].upper() == 'NC':
            self.invert = 1

        self.recycle_secs = self.config['recycle_time']

        self.hw_switch, self.number = (
            self.platform.configure_switch(self.config))


class ReconfiguredSwitch():
    # can overwrite platform specific config parameters and invert

    def __init__(self, switch, config_switch_overwrite, invert):
        self._config_overwrite = config_switch_overwrite
        switch.machine.config_validator.validate_config(
            "switch_overwrites", config_switch_overwrite, switch.name,
            base_spec=switch.platform.get_switch_overwrite_section())
        self._switch = switch
        self._invert = invert

    @staticmethod
    def filter_from_config(config):
        # for transition
        # TODO: remove in 0.31
        whitelist = ["debounce"]
        filtered_config = {}
        for key in config:
            if key in whitelist:
                filtered_config[key] = config[key]

        return filtered_config

    def __getattr__(self, item):
        return getattr(self._switch, item)

    @property
    def invert(self):
        if bool(self._invert) != bool(self._switch.invert):
            return 1
        else:
            return 0

    @property
    def config(self):
        config = copy.deepcopy(self._switch.config)
        for name, item in self._config_overwrite.items():
            if item is not None:
                config[name] = item

        return config
