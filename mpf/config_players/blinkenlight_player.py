"""Blinkenlight config player."""
import uuid

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
                label = s['label'] or uuid.uuid4()
                self.add_color(blinkenlight, s['color'], label, priority + s['priority'], context)
            elif action == 'remove':
                self.remove_color(blinkenlight, s['label'])
            elif action == 'remove_mode':
                self.remove_context_colors(blinkenlight, context)
            elif action == 'remove_all':
                self.remove_all_colors(blinkenlight)

    @staticmethod
    def add_color(blinkenlight, color, label, priority, context):
        """Instructs a blinkenlight to add a color to its list of colors."""
        if blinkenlight is None:
            return
        blinkenlight.add_color(color, label, priority, context)

    @staticmethod
    def remove_all_colors(blinkenlight):
        """Instructs a blinkenlight to remove all of its colors."""
        if blinkenlight is None:
            return
        blinkenlight.remove_all_colors()

    @staticmethod
    def remove_color(blinkenlight, label):
        """Instructs a blinkenlight to remove a color with a given label from its list of colors."""
        if blinkenlight is None:
            return
        blinkenlight._remove_color_with_label(label)

    @staticmethod
    def remove_context_colors(blinkenlight, context):
        """Instructs a blinkenlight to remove all colors that were added by a given context from its list of colors."""
        if blinkenlight is None:
            return
        blinkenlight.remove_color_with_context(context)

    def clear_context(self, context):
        """Clear the context. In our case, this means remove the mode colors from all blinkenlights."""
        for blinkenlight in self.machine.blinkenlights:
            self.remove_context_colors(blinkenlight, context)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(color=value)
