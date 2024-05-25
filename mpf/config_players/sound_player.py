"""Sound player plugin for MPF to support GMC."""
from functools import partial
from mpf.config_players.plugin_player import PluginPlayer


class SoundPlayer(PluginPlayer):

    """Base class for part of the sound player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mpf-mc. MPF finds this instance because the mpf-mc setup.py
    has the following entry_point configured:

        sound_player=mpfmc.config_players.sound_player:register_with_mpf

    """

    config_file_section = 'sound_player'
    show_section = 'sounds'

    def _validate_config_item(self, device, device_settings):
        # device is slide name, device_settings is configuration

        device_settings = self.machine.config_validator.validate_config(
            'sound_player', device_settings)

        return_dict = dict()
        return_dict[device] = device_settings

        return return_dict

    def _register_trigger(self, event, **kwargs):
        """Register trigger via BCP for MC."""
        del kwargs
        client = self.machine.bcp.transport.get_named_client("local_display")
        if client:
            self.machine.bcp.interface.add_registered_trigger_event_for_client(client, event)
        else:
            self.machine.events.add_handler("bcp_clients_connected", partial(self._register_trigger, event))
