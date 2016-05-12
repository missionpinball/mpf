from mpf.core.config_player import ConfigPlayer


class PluginPlayer(ConfigPlayer):
    """Base class for a remote ConfigPlayer that is registered as a plug-in to
    MPF. This class is created on the MPF side of things.
    """

    def __repr__(self):
        return 'PluginPlayer.{}'.format(self.show_section)

    def get_express_config(self, value):
        del value
        raise AssertionError("Plugin Player does not support express config")

    def register_player_events(self, config, mode=None, priority=0):
        """ Overrides this method in the base class and registers the
        config_player events to send the trigger via BCP instead of calling
        the local play() method.

        """
        event_list = list()

        for event in config:
            self.machine.bcp.add_registered_trigger_event(event)
            event_list.append(event)

        return event_list

    def unload_player_events(self, event_list):
        for event in event_list:
            self.machine.bcp.remove_registered_trigger_event(event)

    def play(self, settings, key=None, priority=0, **kwargs):
        self.machine.bcp.bcp_trigger(name='{}_play'.format(self.show_section),
                                     **settings)

    #     settings = deepcopy(settings)
    #     super().play(settings, key, priority, hold, play_kwargs, **kwargs)
    #
    # def play(self, settings, key=None, priority=0, **kwargs):
    #
    #     try:
    #         prior_play_kwargs = play_kwargs.pop('play_kwargs', None)
    #         settings['play_kwargs'] = prior_play_kwargs.update(play_kwargs)
    #         settings['play_kwargs'].update(kwargs)
    #     except AttributeError:
    #         settings['play_kwargs'] = play_kwargs
    #
    #     self.machine.bcp.bcp_trigger(name='{}_play'.format(self.show_section),
    #                                  **settings)
