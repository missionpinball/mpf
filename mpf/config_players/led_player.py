from mpf.core.config_player import ConfigPlayer
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util


class LedPlayer(ConfigPlayer):
    config_file_section = 'led_player'
    show_section = 'leds'
    machine_collection_name = "leds"

    # pylint: disable-msg=too-many-arguments
    def play(self, settings, mode=None, caller=None, priority=0,
             play_kwargs=None, hold=False, **kwargs):

        if 'leds' in settings:
            settings = settings['leds']

        for led, s in settings.items():
            s['color'] = RGBColor(s['color'])

            try:
                led.color(**s)
                if caller:
                    self.caller_target_map[caller].add(led)

            except AttributeError:
                if not led.startswith('('):
                    self.machine.leds[led].color(**s)

                    if caller:
                        self.caller_target_map[caller].add(
                            self.machine.leds[led])

    def clear(self, caller, priority):
        try:
            for led in self.caller_target_map[caller]:
                led.clear_priority(priority)
        except KeyError:
            pass

    def get_express_config(self, value):
        value = str(value).replace(' ', '').lower()
        fade = 0
        if '-f' in value:
            composite_value = value.split('-f')

            # test that the color is valid, but we don't save it now so we can
            # dynamically set it later
            RGBColor(RGBColor.string_to_rgb(composite_value[0]))

            value = composite_value[0]
            fade = Util.string_to_ms(composite_value[1])

        return dict(color=value, fade=fade)

    def get_full_config(self, value):
        super().get_full_config(value)
        value['fade_ms'] = value.pop('fade')
        return value

player_cls = LedPlayer
