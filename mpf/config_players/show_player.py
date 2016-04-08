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
                try:
                    self.machine.shows[show].play(mode=mode,
                                                  play_kwargs=play_kwargs, **s)
                except KeyError:
                    raise KeyError("Cannot play show '{}'. No show with that "
                                   "name.".format(show))

            elif s['action'].lower() == 'stop':
                for running_show in (
                        self.machine.show_controller.get_running_shows(show)):
                    running_show.stop(s['hold'])

            elif s['action'].lower() == 'pause':
                for running_show in (
                        self.machine.show_controller.get_running_shows(show)):
                    running_show.pause()

            elif s['action'].lower() == 'resume':
                for running_show in (
                        self.machine.show_controller.get_running_shows(show)):
                    running_show.resume()

            elif s['action'].lower() == 'advance':
                for running_show in (
                        self.machine.show_controller.get_running_shows(show)):
                    running_show.advance()

            elif s['action'].lower() == 'update':
                for running_show in (
                        self.machine.show_controller.get_running_shows(show)):
                    running_show.update(play_kwargs=play_kwargs, **s)

    def clear(self, caller, priority):
        self.machine.show_controller.stop_shows_by_mode(caller)

    def get_express_config(self, value):
        return dict()

player_cls = ShowPlayer
