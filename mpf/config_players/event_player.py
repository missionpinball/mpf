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
        """Initialise EventPlayer."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Post (delayed) events."""
        for event, s in settings.items():
            s = deepcopy(s)
            event_dict = self.machine.placeholder_manager.parse_conditional_template(event)

            if event_dict.condition and not event_dict.condition.evaluate(kwargs):
                continue

            if event_dict.number:
                delay = Util.string_to_ms(event_dict.number)
                self.delay.add(callback=self._post_event, ms=delay,
                               event=event_dict.name, s=s, **kwargs)
            else:
                self._post_event(event_dict.name, s, **kwargs)

    def _post_event(self, event, s, **kwargs):
        event_name_placeholder = TextTemplate(self.machine, event.replace("(", "{").replace(")", "}"))
        for key, param in s.items():
            if isinstance(param, dict):
                s[key] = self._evaluate_event_param(param, kwargs)
        self.machine.events.post(event_name_placeholder.evaluate(kwargs), **s)

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
