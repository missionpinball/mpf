"""Base class used for things that "play" from the config files, such as
WidgetPlayer, SlidePlayer, etc."""
from mpf.core.config_validator import ConfigValidator
from mpf.core.device import Device


class ConfigPlayer(object):
    config_file_section = None
    show_section = None
    machine_collection_name = None

    show_players = dict()
    config_file_players = dict()

    def __init__(self, machine):
        self.machine = machine
        self.caller_target_map = dict()
        '''Dict of callers which called this config player. Will be used with
        a clear method. Different config players can use this for different
        things. See the LedPlayer for an example.'''

        self.machine.mode_controller.register_start_method(
                self.register_player_events, self.config_file_section)

        ConfigPlayer.show_players[self.show_section] = self
        ConfigPlayer.config_file_players[self.config_file_section] = self

        self.machine.events.add_handler('init_phase_1', self._initialize)

    def __repr__(self):
        return 'ConfigPlayer.{}'.format(self.show_section)

    def _initialize(self):
        if self.machine_collection_name:
            self.device_collection = getattr(self.machine,
                                             self.machine_collection_name)
        else:
            self.device_collection = None

        self.machine.mode_controller.register_load_method(
                self.process_mode_config, self.config_file_section)

        # Look through the machine config for config_player sections and
        # for shows to validate and process
        if self.config_file_section in self.machine.config:
            # Validate
            self.machine.config[self.config_file_section] = (
                self.validate_config(
                    self.machine.config[self.config_file_section]))

            self.register_player_events(
                self.machine.config[self.config_file_section])

    def validate_config(self, config):
        # called first, before config file is cached. Not called if config file
        # is read from cache
        validated_config = dict()

        for event, settings in config.items():
            validated_config[event] = dict()
            validated_config[event][self.show_section] = dict()

            # settings here is the same as a show entry, so we process with
            # that
            if not isinstance(settings, dict):
                settings = {settings: dict()}

            # settings here are dicts of devices/settings
            for device, device_settings in settings.items():
                validated_config[event][self.show_section].update(
                    self.validate_show_config(device, device_settings))

        return validated_config

    def validate_show_config(self, device, device_settings):
        # override if you need a different show processor from config file
        # processor

        # the input values are this section's single step in a show.

        # keys are device names
        # vales are either scalars with express settings, or dicts with full
        # settings

        if device_settings is None:
            device_settings = device

        if not isinstance(device_settings, dict):
            # express config, convert to full
            device_settings = self.get_express_config(device_settings)

        device_settings = self.get_full_config(device_settings)
        # Now figure out if our device is a single or a tag

        try:

            if self.device_collection:
                devices =  self.device_collection.items_tagged(device)

                if not devices:
                    devices = [self.device_collection[device]]

            else:
                devices = [device]

        except KeyError:
            devices = [device]

        return_dict = dict()
        for device in devices:
            return_dict[device] = device_settings

        return return_dict

    def process_mode_config(self, config, root_config_dict, **kwargs):
        # handles validation and processing of mode config
        config = self.validate_config(config)
        root_config_dict[self.config_file_section] = config


    def process_config(self, config, **kwargs):
        # called every time mpf starts, regardless of whether config was built
        # from cache or config files
        del kwargs
        return config

    def process_show_config(self, config):
        # override if you need a different show processor from config file
        # processor
        return config

    def get_express_config(self, value):
        """Implements "express" settings for this config_player which is what
        happens when a config is passed as a string instead of a full config
        dict. (This is detected automatically and this method is only called
        when the config is not a dict.)

        For example, the led_player uses the express config to parse a string
        like 'ff0000-f.5s' and translate it into:

        color: 220000
        fade: 500

        Since every config_player is different, this method raises a
        NotImplementedError and most be configured in the chiild class.

        Args:
            value: The single line string value from a config file.

        Returns:
            A dictionary (which will then be passed through the config
            validator)

        """
        raise NotImplementedError(self.config_file_section)

    def get_full_config(self, value):
        return self.machine.config_validator.validate_config(
            self.config_file_section, value, base_spec='config_player_common')

    def register_player_events(self, config, mode=None, priority=0):
        # config is localized
        key_list = list()

        for event, settings in config.items():
            key_list.append(self.machine.events.add_handler(
                    event=event,
                    handler=self.play,
                    priority=priority,
                    mode=mode,
                    settings=settings))

        return self.unload_player_events, key_list

    def unload_player_events(self, key_list):
        self.machine.events.remove_handlers_by_keys(key_list)

    def additional_processing(self, config):
        return config

    def play(self, settings, mode=None, caller=None, **kwargs):
        # Be sure to include **kwargs in your subclass since events could come
        # in with any parameters

        # todo detect whether this has a single parent key

        if caller and caller not in self.caller_target_map:
            self.caller_target_map[caller] = set()

        # todo mode and priority

        # if mode:
        #     if not mode.active:
        #         return
        #
        #     if 'priority' not in settings:
        #         settings['priority'] = mode.priority
        #     else:
        #         settings['priority'] += mode.priority

    def clear(self, caller, priority):
        pass

    def expand_device_list(self, device):
        if isinstance(device, Device):
            return list(device)

        try:
            return self.device_collection[device]
        except KeyError:
            return self.device_collection.items_tagged(device)

