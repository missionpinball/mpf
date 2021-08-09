"""Light config player."""
from copy import deepcopy
from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util


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
            action = s['action']
            if action == 'add':
                self._add_color(blinkenlight, s['color'], s['key'])
            elif action == 'remove':
                self._remove_color(blinkenlight, s['key'])
            elif action == 'removeall':
                self._remove_all_colors(blinkenlight)
            blinkenlight._restart()

    def _add_color(self, blinkenlight, color, key):
        if blinkenlight is None:
            return
        blinkenlight.add_color(color, key)

    def _remove_all_colors(self, blinkenlight):
        if blinkenlight is None:
            return
        blinkenlight.remove_all_colors()

    def _remove_color(self, blinkenlight, key):
        if blinkenlight is None:
            return
        blinkenlight.remove_color_with_key(key)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(ms=value)
