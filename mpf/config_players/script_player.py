from mpf.core.config_player import ConfigPlayer


class ScriptPlayer(ConfigPlayer):
    config_file_section = 'script_player'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)

        for s in settings:
            # settings is a list of one or more light script configs

            self.machine.show_controller.create_show_from_script(
                script=s['script'],
                lights=s['lights'],
                leds=s['leds'],
                light_tags=s['light_tags'],
                led_tags=s['led_tags'],
                key=s['key']
            )

player_cls = ScriptPlayer