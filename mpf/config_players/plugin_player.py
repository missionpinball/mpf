from copy import deepcopy

from mpf.core.config_player import ConfigPlayer


class PluginPlayer(ConfigPlayer):
    """Base class for a remote ConfigPlayer that is registered as a plug-in to
    MPF. This class is created on the MPF side of things.
    """

    def _initialize(self):
        # overrides base method to just look for this config_player's section
        # in the config files for the purpose of adding event triggers. No
        # need to do validation since that's handled on the remote side.

        # future feature could be to make this switchable so a plugin could
        # ask MPF to do validation.

        if self.config_file_section in self.machine.config:
            self.register_player_events(
                self.machine.config[self.config_file_section])

    def register_player_events(self, config, mode=None, priority=0):
        """ Overrides this method in the base class and registers the
        config_player events to send the trigger via BCP instead of calling
        the local play() method.

        """
        event_list = list()

        for event in config:
            self.machine.bcp.add_registered_trigger_event(event)
            event_list.append(event)

        return self.unload_player_events, event_list

    def unload_player_events(self, event_list):
        for event in event_list:
            self.machine.bcp.remove_registered_trigger_event(event)

    def play(self, settings, mode=None, caller=None, priority=None,
             play_kwargs=None, **kwargs):
        """Only used during shows."""

        prior_play_kwargs = play_kwargs.pop('play_kwargs', None)

        # update in this roundabout way so any kwargs tied to this play call
        # overwrite any from a config
        if prior_play_kwargs:
            settings['play_kwargs'] = prior_play_kwargs.update(play_kwargs)
        else:
            settings['play_kwargs'] = play_kwargs

        settings['play_kwargs'].update(kwargs)

        self.machine.bcp.bcp_trigger(name='{}_play'.format(self.show_section),
                                     **settings)
