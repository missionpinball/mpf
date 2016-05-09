from copy import deepcopy

from mpf.core.config_player import ConfigPlayer


class ShowPlayer(ConfigPlayer):
    config_file_section = 'show_player'
    show_section = 'shows'
    device_collection = None

    def _play(self, settings, key, priority, play_kwargs, **kwargs):
        # if not play_kwargs:
        #     play_kwargs = kwargs
        # else:
        #     play_kwargs.update(kwargs)

        # todo should show_tokens be part of settings?

        if 'shows' in settings:
            settings = settings['shows']

        settings = deepcopy(settings)

        show_tokens = kwargs.get('show_tokens', None)

        for show, s in settings.items():
            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            if not s['key']:
                s['key'] = key

                # todo need to add this key back to the config player

            if s['action'].lower() == 'play':
                try:
                    self.machine.shows[show].play(
                                                  show_tokens=show_tokens,
                                                  priority=s['priority'],
                                                  hold=s['hold'],
                                                  speed=s['speed'],
                                                  start_step=s['start_step'],
                                                  loops=s['loops'],
                                                  sync_ms=s['sync_ms'],
                                                  reset=s['reset'],
                                                  manual_advance=s[
                                                      'manual_advance'],
                                                  key=s['key']
                                                  )
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
                    running_show.update(show_tokens=show_tokens,
                                        priority=s['priority'])

    def _clear(self, key):
        self.machine.show_controller.stop_shows_by_key(key)

    def get_express_config(self, value):
        return dict()

player_cls = ShowPlayer
