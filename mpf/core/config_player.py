"""Base class used for things that "play" from the config files, such as WidgetPlayer, SlidePlayer, etc."""
import abc


class ConfigPlayer(object, metaclass=abc.ABCMeta):

    """Base class for players which play things based on config."""

    config_file_section = None
    show_section = None
    machine_collection_name = None

    def __init__(self, machine):
        """Initialise config player."""
        self.device_collection = None

        self.machine = machine

        # MPF only
        if hasattr(self.machine, "show_controller"):
            self.machine.show_controller.show_players[self.show_section] = self

        self._add_handlers()

        self.mode_event_keys = dict()
        self.instances = dict()
        self.instances['_global'] = dict()
        self.instances['_global'][self.config_file_section] = dict()

    def _add_handlers(self):
        self.machine.events.add_handler('init_phase_1', self._initialize_in_mode)
        self.machine.events.add_handler('init_phase_1', self._initialise_system_wide)

    def __repr__(self):
        """Return string representation."""
        return 'ConfigPlayer.{}'.format(self.show_section)

    def _initialize_in_mode(self):
        self.machine.mode_controller.register_load_method(
            self.process_mode_config, self.config_file_section)

        self.machine.mode_controller.register_start_method(
            self.mode_start, self.config_file_section)

        # Look through the machine config for config_player sections and
        # for shows to validate and process

        # if self.config_file_section in self.machine.config:

    def _initialise_system_wide(self):
        if self.machine_collection_name:
            self.device_collection = getattr(self.machine,
                                             self.machine_collection_name)
        else:
            self.device_collection = None

        if (self.config_file_section in self.machine.config and
                self.machine.config[self.config_file_section]):

            # Validate
            self.machine.config[self.config_file_section] = (
                self.validate_config(
                    self.machine.config[self.config_file_section]))

            self.register_player_events(
                self.machine.config[self.config_file_section])

    def validate_config(self, config):
        """Validate this player's section of a config file (either a machine-wide config or a mode config).

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
            validated_config[event] = self.validate_config_entry(settings, event)

        return validated_config

    def validate_config_entry(self, settings, name):
        """Validate one entry of this player."""
        raise NotImplementedError("implement")

    def _parse_config(self, config, name):
        if isinstance(config, (str, int, float, type(None))):
            # express config, convert to full
            config = self.get_express_config(config)
        elif isinstance(config, list):
            # list config. convert from list to full
            config = self.get_list_config(config)

        if not isinstance(config, dict):
            raise AssertionError("Player config for {} is supposed to be dict. Config: {}".
                                 format(name, str(config)))

        return self.get_full_config(config)

    def process_mode_config(self, config, root_config_dict, mode, **kwargs):
        """Parse mode config."""
        del kwargs
        # handles validation and processing of mode config
        config = self.validate_config(config)
        root_config_dict[self.config_file_section] = config
        if mode.name not in self.instances:
            self.instances[mode.name] = dict()
        if self.config_file_section not in self.instances[mode.name]:
            self.instances[mode.name][self.config_file_section] = dict()

    def _get_full_context(self, context):
        return context + "." + self.config_file_section

    def _get_instance_dict(self, context):
        return self.instances[context][self.config_file_section]

    def _reset_instance_dict(self, context):
        self.instances[context][self.config_file_section] = dict()

    @classmethod
    def process_config(cls, config, **kwargs):
        """Process system-wide config.

        Called every time mpf starts, regardless of whether config was built
        from cache or config files.
        """
        del kwargs
        return config

    def get_list_config(self, value):
        """Parse config list."""
        del value
        raise AssertionError("Player {} does not support lists.".format(self.config_file_section))

    @abc.abstractmethod
    def get_express_config(self, value):
        """Parse short config version.

        Implements "express" settings for this config_player which is what
        happens when a config is passed as a string instead of a full config
        dict. (This is detected automatically and this method is only called
        when the config is not a dict.)

        For example, the led_player uses the express config to parse a string
        like 'ff0000-f.5s' and translate it into:

        color: 220000
        fade: 500

        Since every config_player is different, this method raises a
        NotImplementedError and most be configured in the child class.

        Args:
            value: The single line string value from a config file.

        Returns:
            A dictionary (which will then be passed through the config
            validator)

        """
        raise NotImplementedError(self.config_file_section)

    def get_full_config(self, value):
        """Return full config."""
        return self.machine.config_validator.validate_config(
            self.config_file_section, value, base_spec='config_player_common')

    def mode_start(self, config, priority, mode):
        """Add events for mode."""
        event_keys = self.register_player_events(config, mode, priority)

        self.mode_event_keys[mode] = event_keys

        return self.mode_stop, mode

    def mode_stop(self, mode):
        """Remove events for mode."""
        self.unload_player_events(self.mode_event_keys.pop(mode, list()))
        self.clear_context(mode.name)

    def clear_context(self, context):
        """Clear the context."""
        pass

    def register_player_events(self, config, mode=None, priority=0):
        """Register events for standalone player."""
        # config is localized
        key_list = list()

        if config:
            for event, settings in config.items():
                key_list.append(
                    self.machine.events.add_handler(
                        event=event,
                        handler=self.config_play_callback,
                        priority=priority,
                        mode=mode,
                        settings=settings))

        return key_list

    def unload_player_events(self, key_list):
        """Remove event for standalone player."""
        self.machine.events.remove_handlers_by_keys(key_list)

    def config_play_callback(self, settings, priority=0, mode=None, **kwargs):
        """Callback for standalone player."""
        # called when a config_player event is posted
        if mode:
            if not mode.active:
                # It's possible that an earlier event could have stopped the
                # mode before this event was handled, so just double-check to
                # make sure the mode is still active before proceeding.
                return

            # calculate the base priority, which is a combination of the mode
            # priority and any priority value
            priority += mode.priority
            context = mode.name
        else:
            context = "_global"

        self.play(settings=settings, context=context, priority=priority, **kwargs)

    def show_play_callback(self, settings, priority, show_tokens, context):
        """Callback if used in a show."""
        # called from a show step
        if context not in self.instances:
            self.instances[context] = dict()

        if self.config_file_section not in self.instances[context]:
            self.instances[context][self.config_file_section] = dict()

        self.play(settings=settings, priority=priority,
                  show_tokens=show_tokens, context=context)

    def show_stop_callback(self, context):
        """Callback if show stops."""
        self.clear_context(context)

    @abc.abstractmethod
    def play(self, settings, context, priority=0, **kwargs):
        """Directly play player."""
        # **kwargs since this is an event callback
        raise NotImplementedError
