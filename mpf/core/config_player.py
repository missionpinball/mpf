"""Base class used for things that "play" from the config files, such as WidgetPlayer, SlidePlayer, etc."""
import abc
from functools import partial
from typing import List

from mpf.core.machine import MachineController
from mpf.core.mode import Mode
from mpf.core.logging import LogMixin
from mpf.exceptions.ConfigFileError import ConfigFileError

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.placeholder_manager import BoolTemplate
    from typing import Dict
    import asyncio


class ConfigPlayer(LogMixin, metaclass=abc.ABCMeta):

    """Base class for players which play things based on config."""

    config_file_section = None          # type: str
    show_section = None                 # type: str
    machine_collection_name = None      # type: str

    __slots__ = ["device_collection", "machine", "mode_event_keys", "instances", "_show_keys"]

    def __init__(self, machine):
        """Initialise config player."""
        super().__init__()
        self.device_collection = None

        self.machine = machine      # type: MachineController

        # MPF only
        if hasattr(self.machine, "show_controller") and self.show_section:
            self.machine.show_controller.show_players[self.show_section] = self

        self._add_handlers()

        self.configure_logging(self.config_file_section)

        self.mode_event_keys = dict()
        self.instances = dict()
        self.instances['_global'] = dict()
        self.instances['_global'][self.config_file_section] = dict()
        self._show_keys = {}

    def _add_handlers(self):
        self.machine.events.add_handler('init_phase_1', self._initialize_in_mode, priority=20)
        self.machine.events.add_handler('init_phase_1', self._initialise_system_wide, priority=1)

    def __repr__(self):
        """Return string representation."""
        return 'ConfigPlayer.{}/{}'.format(self.config_file_section, self.show_section)

    def _initialize_in_mode(self, **kwargs):
        del kwargs
        self.machine.mode_controller.register_load_method(
            self.process_mode_config, self.config_file_section)

        self.machine.mode_controller.register_start_method(
            self.mode_start, self.config_file_section)

        # Look through the machine config for config_player sections and
        # for shows to validate and process

        # if self.config_file_section in self.machine.config:

    def _initialise_system_wide(self, **kwargs):
        del kwargs
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
        if config is None:
            raise AssertionError("Empty config player {}".format(name))
        elif isinstance(config, (str, int, float)):
            # express config, convert to full
            config = self.get_express_config(config)
        elif isinstance(config, list):
            # list config. convert from list to full
            config = self.get_list_config(config)   # pylint: disable-msg=assignment-from-no-return

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
        if context not in self.instances or self.config_file_section not in self.instances[context]:
            self.warning_log("Config player {} is missing context {}".format(self.config_file_section, context))
            return {}
        return self.instances[context][self.config_file_section]

    def _reset_instance_dict(self, context):
        if context not in self.instances:
            self.instances[context] = {}
        self.instances[context][self.config_file_section] = dict()

    @classmethod
    def process_config(cls, config, **kwargs):
        """Process system-wide config.

        Called every time mpf starts, regardless of whether config was built
        from cache or config files.
        """
        del kwargs
        return config

    def get_list_config(self, value) -> List[str]:
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

    @staticmethod
    def _parse_event_priority(event, priority):
        # todo should we move this to EventManager so we can use the dot
        # priority shift notation for all event handlers?

        if event.find(".") > 0 and (event.find("{") < 0 or event.find(".") < event.find("{")):
            new_event = event[:event.find(".")]
            if event.find("{") > 0:
                priority += int(event[event.find(".") + 1:event.find("{")])
                new_event += event[event.find("{"):]
            else:
                priority += int(event[event.find(".") + 1:])
            event = new_event
        return event, priority

    @staticmethod
    def is_entry_valid_outside_mode(settings) -> bool:
        """Return true if this entry may run without a game and player."""
        del settings
        return True

    # pylint: disable-msg=too-many-arguments
    def _create_subscription(self, template_str, subscription_list, settings, priority, mode):
        template = self.machine.placeholder_manager.build_bool_template(template_str)
        if mode:
            context = mode.name
            actual_priority = priority + mode.priority
        else:
            context = "_global"
            actual_priority = priority

        self._update_subscription(template, subscription_list, settings, actual_priority, context, None)

    # pylint: disable-msg=too-many-arguments
    def _update_subscription(self, template, subscription_list, settings, priority, context, future):
        if future and future.cancelled():
            return
        value, subscription = template.evaluate_and_subscribe([])
        subscription_list[template] = subscription
        subscription.add_done_callback(
            partial(self._update_subscription, template, subscription_list, settings, priority, context))
        self.handle_subscription_change(value, settings, priority, context)

    # pylint: disable-msg=no-self-use
    def handle_subscription_change(self, value, settings, priority, context):
        """Handle the change of a subscription."""
        del value
        del settings
        del priority
        del context
        raise AssertionError("Subscriptions are not supported in this player.")

    def register_player_events(self, config, mode: Mode = None, priority=0):
        """Register events for standalone player."""
        # config is localized
        key_list = list()
        subscription_list = dict()      # type: Dict[BoolTemplate, asyncio.Future]

        if config:
            for event, settings in config.items():
                # prevent runtime crashes
                if (not mode or (mode and not mode.is_game_mode)) and not self.is_entry_valid_outside_mode(settings):
                    raise ConfigFileError("Section not valid outside of game modes. {} {}:{} Mode: {}".format(
                        self, event, settings, mode
                    ), 1, self.config_file_section)
                if event.startswith("{") and event.endswith("}"):
                    condition = event[1:-1]
                    self._create_subscription(condition, subscription_list, settings, priority, mode)
                else:
                    event, actual_priority = self._parse_event_priority(event, priority)

                    if mode and event in mode.config['mode']['start_events']:
                        self.machine.log.error(
                            "{0} mode's {1}: section contains a \"{2}:\" event "
                            "which is also in the start_events: for the {0} mode. "
                            "Change the {1}: {2}: event name to "
                            "\"mode_{0}_started:\"".format(
                                mode.name, self.config_file_section, event))

                        raise ValueError(
                            "{0} mode's {1}: section contains a \"{2}:\" event "
                            "which is also in the start_events: for the {0} mode. "
                            "Change the {1}: {2}: event name to "
                            "\"mode_{0}_started:\"".format(
                                mode.name, self.config_file_section, event))

                    key_list.append(
                        self.machine.events.add_handler(
                            event=event,
                            handler=self.config_play_callback,
                            calling_context=event,
                            priority=actual_priority,
                            mode=mode,
                            settings=settings))

        return key_list, subscription_list

    def unload_player_events(self, key_list):
        """Remove event for standalone player."""
        for future in key_list[1].values():
            future.cancel()
        self.machine.events.remove_handlers_by_keys(key_list[0])

    def config_play_callback(self, settings, calling_context, priority=0, mode=None, **kwargs):
        """Handle play callback for standalone player."""
        # called when a config_player event is posted
        if mode:
            if not mode.active:
                # It's possible that an earlier event could have stopped the
                # mode before this event was handled, so just double-check to
                # make sure the mode is still active before proceeding.
                return None

            # calculate the base priority, which is a combination of the mode
            # priority and any priority value
            priority += mode.priority
            context = mode.name
        else:
            context = "_global"

        return self.play(settings=settings, context=context, calling_context=calling_context, priority=priority,
                         **kwargs)

    # pylint: disable-msg=too-many-arguments
    def show_play_callback(self, settings, priority, calling_context, show_tokens, context, start_time):
        """Handle show callback."""
        # called from a show step
        if context not in self.instances:
            self.instances[context] = dict()

        if self.config_file_section not in self.instances[context]:
            self.instances[context][self.config_file_section] = dict()

        # register bcp events
        config = {'bcp_connection': settings['bcp_connection']} if 'bcp_connection' in settings else {}
        event_keys = self.register_player_events(config, None, priority)
        self._show_keys[context + self.config_file_section] = event_keys

        self.play(settings=settings, priority=priority, calling_context=calling_context,
                  show_tokens=show_tokens, context=context, start_time=start_time)

    def show_stop_callback(self, context):
        """Handle show stop."""
        self.unload_player_events(self._show_keys[context + self.config_file_section])
        del self._show_keys[context + self.config_file_section]

        self.clear_context(context)

    @abc.abstractmethod
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Directly play player."""
        # **kwargs since this is an event callback
        raise NotImplementedError
