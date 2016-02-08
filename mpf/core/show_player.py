from mpf.core.config_player import ConfigPlayer


class ShowPlayer(ConfigPlayer):
    config_file_section = 'show_player'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)

        for s in settings:  # settings is a list of one or more show configs

            name = s['show']

            # todo make sure this is right. Probably want to put better logic
            # into the base class
            priority = s['priority']

            if not priority:
                priority = 0

            if s['action'].lower() == 'play':
                self.machine.show_controller.play_show(name, priority,
                                                       **kwargs)

            elif s['action'].lower() == 'stop':
                self.machine.show_controller.stop_show(name, **kwargs)
