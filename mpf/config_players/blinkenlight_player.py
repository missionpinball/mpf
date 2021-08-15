"""Light config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


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
                self.add_color(blinkenlight, s['color'], s['key'], priority + s['priority'])
            elif action == 'remove':
                self.remove_color(blinkenlight, s['key'])
            elif action == 'removeall':
                self.remove_all_colors(blinkenlight)

    @staticmethod
    def add_color(blinkenlight, color, key, priority):
        if blinkenlight is None:
            return
        blinkenlight.add_color(color, key, priority)

    @staticmethod
    def remove_all_colors(blinkenlight):
        if blinkenlight is None:
            return
        blinkenlight.remove_all_colors()

    @staticmethod
    def remove_color(blinkenlight, key):
        if blinkenlight is None:
            return
        blinkenlight.remove_color_with_key(key)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(ms=value)
