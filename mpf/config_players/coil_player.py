"""Coil config player."""
from copy import deepcopy

from mpf.config_players.device_config_player import DeviceConfigPlayer


class CoilPlayer(DeviceConfigPlayer):

    """Triggers coils based on config."""

    config_file_section = 'coil_player'
    show_section = 'coils'

    def play(self, settings, context, priority=0, **kwargs):
        """Enable, Pulse or disable coils."""
        del kwargs
        instance_dict = self._get_instance_dict(context)

        for coil, s in settings.items():
            s = deepcopy(s)
            action = s.pop('action')
            try:
                coil = getattr(coil, action)
            except AttributeError:
                coil = getattr(self.machine.coils[coil], action)

            if action in ("disable", "off") and coil.name in instance_dict:
                del instance_dict[coil.name]
            elif action in ("on", "enable"):
                instance_dict[coil.name] = coil

            coil(**s)

    def clear_context(self, context):
        """Disable enabled coils."""
        instance_dict = self._get_instance_dict(context)
        for coil in instance_dict.values():
            coil.disable()

        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse short config version."""
        try:
            value = int(value)
            return dict(action='pulse', milliseconds=value)
        except (TypeError, ValueError):
            pass

        action = 'pulse'

        if value in ('disable', 'off'):
            action = 'disable'

        elif value in ('enable', 'on'):
            action = 'enable'

        return dict(action=action, power=1.0)


player_cls = CoilPlayer
