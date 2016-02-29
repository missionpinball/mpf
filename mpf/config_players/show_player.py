from mpf.core.config_player import ConfigPlayer


class ShowPlayer(ConfigPlayer):
    config_file_section = 'show_player'
    show_section = 'shows'

    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        for s in settings:  # settings is a list of one or more show configs

            name = s['show']

            # todo make sure this is right. Probably want to put better logic
            # into the base class
            priority = s['priority']

            if not priority:
                priority = 0

            if s['action'].lower() == 'play':
                self.machine.shows[name].play(priority=priority, **kwargs)

            elif s['action'].lower() == 'stop':
                self.machine.shows[name].stop(**kwargs)

player_cls = ShowPlayer