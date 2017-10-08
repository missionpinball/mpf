"""Coil config player."""
from copy import deepcopy

from mpf.config_players.device_config_player import DeviceConfigPlayer


class CoilPlayer(DeviceConfigPlayer):

    """Triggers coils based on config."""

    config_file_section = 'coil_player'
    show_section = 'coils'
    machine_collection_name = 'coils'

    def play(self, settings, context: str, calling_context: str, priority: int = 0, **kwargs):
        """Enable, Pulse or disable coils."""
        del kwargs
        del calling_context
        instance_dict = self._get_instance_dict(context)

        for coil, s in settings.items():
            s = deepcopy(s)
            action = s.pop('action')
            coil_action = getattr(coil, action)

            if action in ("disable", "off") and coil.name in instance_dict:
                del instance_dict[coil.name]
            elif action in ("on", "enable"):
                instance_dict[coil.name] = coil

            coil_action(**s)

    def clear_context(self, context):
        """Disable enabled coils."""
        instance_dict = self._get_instance_dict(context)
        for coil in instance_dict.values():
            coil.disable()

        self._reset_instance_dict(context)

    def get_express_config(self, value: str):
        """Parse short config version."""
        try:
            int_value = int(value)
            return dict(action='pulse', pulse_ms=int_value)
        except (TypeError, ValueError):
            pass

        action = 'pulse'

        if value in ('disable', 'off'):
            action = 'disable'

        elif value in ('enable', 'on'):
            action = 'enable'

        return dict(action=action, power=1.0)
