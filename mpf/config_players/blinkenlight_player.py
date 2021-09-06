"""Blinkenlight config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.devices.blinkenlight import Blinkenlight


class BlinkenlightPlayer(DeviceConfigPlayer):

    """Blinks lights different colors based on config."""

    config_file_section = 'blinkenlight_player'
    show_section = 'blinkenlights'
    machine_collection_name = 'blinkenlights'
    allow_placeholders_in_keys = True

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Adds/removes colors to blink."""
        del kwargs

        for blinkenlight, s in settings.items():
            if not isinstance(blinkenlight, str):
                action = s['action']
                key = context + s['key'] if s["key"] else context
                if action == 'add':
                    self._add_color(blinkenlight, s['color'], key, priority + s['priority'])
                    self._get_instance_dict(context)[(key, blinkenlight)] = blinkenlight
                elif action == 'remove':
                    self._remove_color(blinkenlight, key)
                    try:
                        del self._get_instance_dict(context)[(key, blinkenlight)]
                    except KeyError:
                        pass
                elif action == 'remove_mode':
                    self.clear_context(context)
                elif action == 'remove_all':
                    self._remove_all_colors(blinkenlight)
                else:
                    raise AssertionError("Unknown action {}".format(action))

    @staticmethod
    def _add_color(blinkenlight: Blinkenlight, color, key, priority):
        """Instructs a blinkenlight to add a color to its list of colors."""
        blinkenlight.add_color(color, key, priority)

    @staticmethod
    def _remove_all_colors(blinkenlight):
        """Instructs a blinkenlight to remove all of its colors."""
        blinkenlight.remove_all_colors()

    @staticmethod
    def _remove_color(blinkenlight, key):
        """Instructs a blinkenlight to remove a color with a given key from its list of colors."""
        blinkenlight.remove_color_with_key(key)

    def clear_context(self, context):
        """Clear the context. In our case, this means remove the mode colors from all blinkenlights."""
        for (key, _), blinkenlight in self._get_instance_dict(context).items():
            blinkenlight.remove_color_with_key(key)
        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        if value in ("stop", "remove"):
            return dict(action="remove")
        return dict(color=value)
