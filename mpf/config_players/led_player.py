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

        del kwargs

        if 'leds' in settings:
            settings = settings['leds']

        for led, s in settings.items():
            s['color'] = RGBColor(s['color'])

            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            if caller:
                s['key'] = caller
            else:
                s['key'] = mode

            try:
                led.color(**s)
                if caller:
                    self.caller_target_map[caller].add(led)

            except AttributeError:
                try:
                    self._led_color(led, caller, **s)
                except KeyError:
                    led_list = Util.string_to_list(led)
                    if len(led_list) > 1:
                        for led1 in led_list:
                            self._led_color(led1, caller, **s)
                    else:
                        for led1 in self.machine.leds.sitems_tagged(led):
                            self._led_color(led1, caller, **s)

    def _led_color(self, led_name, caller=None, **s):
        self.machine.leds[led_name].color(**s)
        if caller:
            self.caller_target_map[caller].add(
                self.machine.leds[led_name])

    def clear(self, caller, priority):

        del priority

        try:
            for led in self.caller_target_map[caller]:
                led.remove_from_stack_by_key(caller)
        except KeyError:
            pass

    def config_play_callback(self, settings, priority=0, mode=None,
                             hold=None, **kwargs):
        # led_player sections from config should set LEDs to hold

        super().config_play_callback(settings=settings, priority=priority,
                                     mode=mode, hold=True, **kwargs)

        # todo change this in the base method?

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
