from copy import deepcopy

from mpf.core.config_player import ConfigPlayer


class ShowPlayer(ConfigPlayer):
    config_file_section = 'show_player'
    show_section = 'shows'
    device_collection = None

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None, priority=0,
             play_kwargs=None, **kwargs):

        if not play_kwargs:
            play_kwargs = kwargs
        else:
            play_kwargs.update(kwargs)

        if 'shows' in settings:
            settings = settings['shows']

        settings = deepcopy(settings)

        for show, s in settings.items():

            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            if s['action'].lower() == 'play':
                self.machine.shows[show].play(mode=mode,
                                              play_kwargs=play_kwargs, **s)

            elif s['action'].lower() == 'stop':
                self.machine.shows[show].stop(play_kwargs=play_kwargs, **s)

    def clear(self, caller, priority):
        self.machine.show_controller.stop_shows_by_mode(caller)

    def get_express_config(self, value):
        return dict()

player_cls = ShowPlayer
