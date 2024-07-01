"""Flasher config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.core.delays import DelayManager
from mpf.core.utility_functions import Util


class FlasherPlayer(DeviceConfigPlayer):

    """Triggers flashers based on config."""

    config_file_section = 'flasher_player'
    show_section = 'flashers'

    __slots__ = ["delay"]

    def __init__(self, machine):
        """Initialize flasher_player."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Flash flashers."""
        del kwargs

        for flasher, s in settings.items():
            if isinstance(flasher, str):
                flasher_names = Util.string_to_event_list(flasher)
                for flasher_name in flasher_names:
                    self._flash(self.machine.lights[flasher_name],
                                duration_ms=s['ms'],
                                color=s['color'],
                                key=context)
            else:
                self._flash(flasher, duration_ms=s['ms'], key=context, color=s['color'])

    def _flash(self, light, duration_ms, key, color):
        light.color(color, fade_ms=0, key=key)
        self.delay.add(duration_ms, self._remove_flash, light=light, key=key)

    @staticmethod
    def _remove_flash(light, key):
        light.remove_from_stack_by_key(key=key, fade_ms=0)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(ms=value)
