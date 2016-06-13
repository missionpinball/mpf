"""Plugin config player."""
from mpf.core.config_player import ConfigPlayer


class PluginPlayer(ConfigPlayer):

    """Base class for a remote ConfigPlayer that is registered as a plug-in to MPF.

    This class is created on the MPF side of things.
    """

    def __repr__(self):
        """Return str representation."""
        return 'PluginPlayer.{}'.format(self.show_section)

    def get_express_config(self, value):
        """Not supported."""
        del value
        raise AssertionError("Plugin Player does not support express config")

    def register_player_events(self, config, mode=None, priority=0):
        """Register player events via BCP.

        Override this method in the base class and registers the
        config_player events to send the trigger via BCP instead of calling
        the local play() method.
        """
        event_list = list()

        for event in config:
            self.machine.bcp.add_registered_trigger_event(event)
            event_list.append(event)

        return event_list

    def unload_player_events(self, event_list):
        """Unload player events via BCP."""
        for event in event_list:
            self.machine.bcp.remove_registered_trigger_event(event)

    def play(self, settings, context, priority=0, **kwargs):
        """Trigger remote player via BCP."""
        self.machine.bcp.bcp_trigger(name='{}_play'.format(self.show_section),
                                     settings=settings, context=context,
                                     priority=priority)
        # todo do we need kwargs here? I think no?
