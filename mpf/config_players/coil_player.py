"""Coil config player."""
from copy import deepcopy
from typing import List

from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.devices.driver import Driver


class CoilPlayer(DeviceConfigPlayer):

    """Triggers coils based on config."""

    config_file_section = 'coil_player'
    show_section = 'coils'
    machine_collection_name = 'coils'

    __slots__ = []  # type: List[str]

    def play(self, settings, context: str, calling_context: str, priority: int = 0, **kwargs):
        """Enable, Pulse or disable coils."""
        del kwargs
        del calling_context
        instance_dict = self._get_instance_dict(context)

        for coil, s in settings.items():
            s = deepcopy(s)
            if not isinstance(coil, Driver):
                self.raise_config_error("Invalid coil name {}".format(coil), 2, context=context)
            action = s.pop('action')

            # delete coil from dict
            try:
                del instance_dict[coil.name]
            except KeyError:
                pass

            if action in ("disable", "off"):
                coil.disable()
            elif action in ("on", "enable"):
                instance_dict[coil.name] = coil
                coil.enable(pulse_ms=s["pulse_ms"], pulse_power=s["pulse_power"], hold_power=s["hold_power"])
            elif action == "pulse":
                coil.pulse(pulse_ms=s['pulse_ms'], pulse_power=s['pulse_power'], max_wait_ms=s['max_wait_ms'])
            else:
                self.raise_config_error("Invalid action {}".format(action), 1, context=context)

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

        return dict(action=action)
