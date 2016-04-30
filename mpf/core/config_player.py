"""Base class used for things that "play" from the config files, such as
WidgetPlayer, SlidePlayer, etc."""
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

        ConfigPlayer.show_players[self.show_section] = self
        ConfigPlayer.config_file_players[self.config_file_section] = self

        self.machine.events.add_handler('init_phase_1', self._initialize)

        self.mode_keys = dict()

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

        self.machine.mode_controller.register_start_method(
                self.mode_start, self.config_file_section)

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
        """Validates this player's section of a config file (either a machine-
        wide config or a mode config).

        Args:
            config: A dict of the contents of this config_player's section
            from the config file. It's assumed that keys are event names, and
            values are settings for what this config_player does when that
            event is posted.

        Returns: A dict in the same format, but passed through the config
            validator.

        """
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
                devices = self.device_collection.items_tagged(device)
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
        del kwargs
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

    def mode_start(self, config, priority, mode):
        event_keys = self.register_player_events(config, mode, priority)

        self.mode_keys[mode] = event_keys

        return self.mode_stop, mode

    def mode_stop(self, mode):
        event_keys = self.mode_keys.pop(mode, list())

        self.unload_player_events(event_keys)
        self.clear(mode, mode.priority)

    def register_player_events(self, config, mode=None, priority=0):
        # config is localized
        key_list = list()

        if config:
            for event, settings in config.items():
                key_list.append(self.machine.events.add_handler(
                        event=event,
                        handler=self.config_play_callback,
                        priority=priority,
                        mode=mode,
                        settings=settings))

        return key_list

    def unload_player_events(self, key_list):
        self.machine.events.remove_handlers_by_keys(key_list)

    def additional_processing(self, config):
        return config

    def config_play_callback(self, settings, priority=0, mode=None,
                             hold=None, **kwargs):
        # called when a config_player event is posted

        # calculate the base priority, which is a combination of the mode
        # priority and any priority value

        if mode:

            if not mode.active:
                # It's possible that an earlier event could have stopped the
                # mode before this event was handled, so just double-check to
                # make sure the mode is still active before proceeding.
                return

            if mode not in self.caller_target_map:
                self.caller_target_map[mode] = set()
                # todo call clear() on mode stop

            priority += mode.priority

        # todo detect whether this has a single parent key

        # todo play_kwargs

        self.play(settings=settings, mode=mode, caller=mode,
                  priority=priority, hold=hold, **kwargs)

    # pylint: disable-msg=too-many-arguments
    def show_play_callback(self, settings, mode, caller, priority,
                           hold, show_tokens):
        # called from a show step

        # todo add caller processing? Or stop_key?
        if caller and caller not in self.caller_target_map:
            self.caller_target_map[caller] = set()

        self.play(settings=settings, mode=mode, caller=caller,
                  priority=priority, show_tokens=show_tokens, hold=hold)

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None, priority=None,
             hold=None, play_kwargs=None, **kwargs):

        raise NotImplementedError

    def clear(self, caller, priority):
        pass

    def expand_device_list(self, device):
        if isinstance(device, Device):
            return list(device)

        try:
            return self.device_collection[device]
        except KeyError:
            return self.device_collection.items_tagged(device)
