from mpf.core.config_player import ConfigPlayer


class CoilPlayer(ConfigPlayer):
    config_file_section = 'coil_player'
    show_section = 'coils'

    def play(self, settings, mode=None, caller=None, **kwargs):
        super().play(settings, mode, caller, **kwargs)

        if 'coils' in settings:
            settings = settings['coils']

        for coil, s in settings.items():
            try:
                getattr(coil, s['action'])(**s)
            except AttributeError:
                getattr(self.machine.coils[coil], s['action'])(**s)

    def get_express_config(self, value):

        try:
            value = int(value)
            return dict(action='pulse', milliseconds=value)
        except (TypeError, ValueError):
            pass

        action = 'pulse'

        if value in ('disable', 'off'):
            action = 'disable'

        elif value in ('enable', 'on'):
            action = 'enable'

        return dict(action=action, power=1.0)


player_cls = CoilPlayer
