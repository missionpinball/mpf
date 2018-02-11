"""Flasher config player."""
from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.core.delays import DelayManager


class FlasherPlayer(DeviceConfigPlayer):

    """Triggers flashers based on config."""

    config_file_section = 'flasher_player'
    show_section = 'flashers'

    def __init__(self, machine):
        """Initialise flasher_player."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine.delayRegistry)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Flash flashers."""
        del kwargs

        for flasher, s in settings.items():
            if isinstance(flasher, str):
                self._flash(self.machine.lights[flasher],
                            duration_ms=s['ms'],
                            key=context)
            else:
                self._flash(flasher, duration_ms=s['ms'], key=context)

    def _flash(self, light, duration_ms, key):
        light.color("white", fade_ms=0, key=key)
        self.delay.add(duration_ms, self._remove_flash, light=light, key=key)

    @staticmethod
    def _remove_flash(light, key):
        light.remove_from_stack_by_key(key=key, fade_ms=0)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(ms=value)
