from mpf.core.config_player import ConfigPlayer


class ShowPlayer(ConfigPlayer):
    config_file_section = 'show_player'
    show_section = 'shows'
    device_collection = None

    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        # This is needed since shows calling shows can be recursive, so
        # we check to make sure we have the actual show settings and not
        # a dict that's one level higher
        if 'shows' in settings:
            settings = settings['shows']

        for show, s in settings.items():
            if s['action'].lower() == 'play':
                self.machine.shows[show].play(**s)

            elif s['action'].lower() == 'stop':
                self.machine.shows[show].stop(**s)

    def get_express_config(self, value):
        return dict()


player_cls = ShowPlayer
