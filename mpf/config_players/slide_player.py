from functools import partial

from mpf.config_players.plugin_player import PluginPlayer
from mpf.core.utility_functions import Util


class SlidePlayer(PluginPlayer):
    """Base class for part of the slide player which runs as part of MPF.

    Note: This class is loaded by MPF and everything in it is in the context of
    MPF, not the mc.
    """
    config_file_section = 'slide_player'
    show_section = 'slides'

    def _validate_config_item(self, device, device_settings):
        # device is slide name, device_settings is configuration

        device_settings = self.machine.config_validator.validate_config(
            'slide_player', device_settings)


        if 'widgets' in device_settings:
            device_settings['widgets'] = self.process_widgets(
                device_settings['widgets'])

        return_dict = dict()
        return_dict[device] = device_settings

        return return_dict

    def process_widgets(self, config):

        if isinstance(config, dict):
            config = [config]

        # Note that we don't reverse the order of the widgets here since
        # they'll be reversed when they're played

        widget_list = list()

        for widget in config:
            widget_list.append(self.process_widget(widget))

        return widget_list

    def _register_trigger(self, event, **kwargs):
        """Register trigger via BCP for MC."""
        del kwargs
        client = self.machine.bcp.transport.get_named_client("local_display")
        if client:
            self.machine.bcp.interface.add_registered_trigger_event_for_client(client, event)
        else:
            self.machine.events.add_handler("bcp_clients_connected", partial(self._register_trigger, event))
