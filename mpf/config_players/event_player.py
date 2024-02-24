"""Event Config Player."""
from copy import deepcopy

from mpf.core.placeholder_manager import TextTemplate

from mpf.config_players.flat_config_player import FlatConfigPlayer
from mpf.core.delays import DelayManager
from mpf.core.utility_functions import Util


class EventPlayer(FlatConfigPlayer):

    """Posts events based on config."""

    config_file_section = 'event_player'
    show_section = 'events'

    __slots__ = ["delay"]

    def __init__(self, machine):
        """initialize EventPlayer."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Post (delayed) events."""
        for event, event_configs in settings.items():
            for s in event_configs:
                if s["condition"] and not s["condition"].evaluate(kwargs):
                    continue

                if s["number"] is not None:
                    self.delay.add(callback=self._post_event, ms=s["number"],
                                   event=event, priority=s["priority"], params=s["params"], **kwargs)
                else:
                    self._post_event(event, s["priority"], s["params"], **kwargs)

    # pylint: disable-msg=too-many-arguments
    def handle_subscription_change(self, value, settings, priority, context, key):
        """Handle subscriptions."""
        instance_dict = self._get_instance_dict(context)
        previous_value = instance_dict.get(key, None)
        if previous_value == value:
            return
        instance_dict[key] = value

        if not value:
            return

        for event, event_configs in settings.items():
            for s in event_configs:
                if s["condition"] and not s["condition"].evaluate({}):
                    continue

                if s["number"] is not None:
                    self.delay.add(callback=self._post_event, ms=s["number"],
                                event=event, priority=s["priority"], params=s["params"])
                else:
                    self._post_event(event, s["priority"], s["params"])

    def _post_event(self, event, priority, params, **kwargs):
        if "(" in event:
            # TODO: move this to parsing time
            event_name_placeholder = TextTemplate(self.machine, event.replace("(", "{").replace(")", "}"))
            event = event_name_placeholder.evaluate(kwargs)
        for key, param in params.items():
            if isinstance(param, dict):
                params = deepcopy(params)
                # TODO: move this to parsing time
                params[key] = self._evaluate_event_param(param, kwargs)
        self.machine.events.post(event, priority=priority, **params)

    def validate_config_entry(self, settings, name):
        """Validate player and expand placeholders."""
        config = super().validate_config_entry(settings, name)
        final_config = {}
        for event, s in config.items():
            if "(" in event:
                if event not in final_config:
                    final_config[event] = []
                final_config[event].append({
                    "condition": None,
                    "number": None,
                    "priority": s["priority"],
                    "params": {k: v for k, v in s.items() if k != "priority"}
                })
            else:
                var = self._parse_and_validate_conditional(event, name)
                if var.name not in final_config:
                    final_config[var.name] = []
                final_config[var.name].append({
                    "condition": var.condition,
                    "number": Util.string_to_ms(var.number) if var.number else None,
                    "priority": s["priority"],
                    "params": {k: v for k, v in s.items() if k != "priority"}
                })
        return final_config

    def _evaluate_event_param(self, param, kwargs):
        if param.get("type") == "float":
            placeholder = self.machine.placeholder_manager.build_float_template(param["value"])
        elif param.get("type") == "int":
            placeholder = self.machine.placeholder_manager.build_int_template(param["value"])
        elif param.get("type") == "bool":
            placeholder = self.machine.placeholder_manager.build_bool_template(param["value"])
        else:
            placeholder = self.machine.placeholder_manager.build_string_template(param["value"])
        return placeholder.evaluate(kwargs)

    def get_list_config(self, value):
        """Parse list."""
        result = {}
        for event in value:
            result[event] = {}
        return result

    def get_express_config(self, value):
        """Parse short config."""
        return self.get_list_config(Util.string_to_event_list(value))
