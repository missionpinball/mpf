"""Light config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer


class BlinkenlightPlayer(DeviceConfigPlayer):

    """Blinks lights different colors based on config."""

    config_file_section = 'blinkenlight_player'
    show_section = 'blinkenlights'
    machine_collection_name = 'blinkenlights'
    allow_placeholders_in_keys = True

    # A set of all the blinkenlights this player has added a color for.
    # We will use this list to remove mode colors when a mode ends.
    blinkenlights = set()

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Adds/removes colors to blink."""
        del kwargs

        for blinkenlight, s in settings.items():
            action = s['action']
            if action == 'add':
                self.add_color(blinkenlight, s['color'], s['key'], priority + s['priority'], context)
                self.blinkenlights.add(blinkenlight)
            elif action == 'remove':
                self.remove_color(blinkenlight, s['key'])
            elif action == 'remove_mode':
                self.remove_mode_colors(blinkenlight, context)
                self.blinkenlights.remove(blinkenlight)
            elif action == 'remove_all':
                self.remove_all_colors(blinkenlight)
                self.blinkenlights.remove(blinkenlight)

    @staticmethod
    def add_color(blinkenlight, color, key, priority, context):
        """Instructs a blinkenlight to add a color to its list of colors."""
        if blinkenlight is None:
            return
        blinkenlight.add_color(color, key, priority, context)

    @staticmethod
    def remove_all_colors(blinkenlight):
        """Instructs a blinkenlight to remove all of its colors."""
        if blinkenlight is None:
            return
        blinkenlight.remove_all_colors()

    @staticmethod
    def remove_color(blinkenlight, key):
        """Instructs a blinkenlight to remove a color with a given key from its list of colors."""
        if blinkenlight is None:
            return
        blinkenlight.remove_color_with_key(key)

    @staticmethod
    def remove_mode_colors(blinkenlight, mode):
        """Instructs a blinkenlight to remove all colors that were added by a given mode from its list of colors."""
        if blinkenlight is None:
            return
        blinkenlight.remove_color_with_mode(mode)

    def mode_stop(self, mode):
        """Remove events for mode."""
        super().mode_stop(mode)
        for blinkenlight in self.blinkenlights:
            self.remove_mode_colors(blinkenlight, mode.name)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(ms=value)
