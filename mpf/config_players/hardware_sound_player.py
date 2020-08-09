"""Config player for sounds on an external sound card."""
from typing import List

from mpf.config_players.device_config_player import DeviceConfigPlayer

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.hardware_sound_system import HardwareSoundSystem   # pylint: disable-msg=cyclic-import,unused-import; # noqa


class HardwareSoundPlayer(DeviceConfigPlayer):

    """Plays sounds on an external sound card."""

    config_file_section = 'hardware_sound_player'
    show_section = 'hardware_sounds'

    __slots__ = []  # type: List[str]

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Play sound on external card."""
        del kwargs
        del context
        del calling_context

        for item, s in settings.items():
            sound_system = s['sound_system']        # type: HardwareSoundSystem
            if "value" in s and s["value"]:
                item = s["value"]

            if s['action'] == "stop":
                sound_system.stop_all_sounds()
            elif s['action'] == "play":
                sound_system.play(item, s["track"])
            elif s['action'] == "play_file":
                sound_system.play_file(item, s.get("platform_options", {}), s["track"])
            elif s['action'] == "text_to_speech":
                sound_system.text_to_speech(item, s.get("platform_options", {}), s["track"])
            elif s['action'] == "set_volume":
                sound_system.set_volume(float(item), s["track"])
            elif s['action'] == "increase_volume":
                sound_system.increase_volume(float(item), s["track"])
            elif s['action'] == "decrease_volume":
                sound_system.decrease_volume(float(item), s["track"])
            else:
                raise AssertionError("Invalid action {}".format(s['action']))

    def get_express_config(self, value):
        """Parse express config."""
        return dict(action=value)

    def get_string_config(self, string):
        """Parse string config."""
        if string == "stop":
            return {string: dict(action="stop")}

        return super().get_string_config(string)
