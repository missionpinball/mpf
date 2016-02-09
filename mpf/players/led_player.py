from mpf.core.config_player import ConfigPlayer
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util


class LedPlayer(ConfigPlayer):
    config_file_section = 'led_player'
    show_section = 'leds'

    def play(self, settings, mode=None, **kwargs):
        super().play(settings, mode, **kwargs)

        for led, s in settings.items():
            led.color(**s)

    def validate_config(self, config):
        # config is localized to the 'leds' section of a show or the
        # 'led_player' section of config

        if not config:
            config = dict()

        if not isinstance(config, dict):
            raise ValueError("Received invalid led player config: "
                             .format(config))

        validated_config = dict()

        for led, value in config.items():
            value = str(value)
            if 'tag|' in led:
                tag = led.split('tag|')[1]
                led_list = self.machine.leds.sitems_tagged(tag)

                if not led_list:
                    self.log.warning("No leds exist for tag '{}'".format(tag))

            else:  # create a single item list of the led
                try:
                    # run it through machine.leds to make sure it's valid
                    led_list = [self.machine.leds[led].name]
                except KeyError:
                    raise ValueError("Found invalid led name '{}' in "
                                     "led show or led_player "
                                     "config".format(led))

            # convert / ensure leds are single ints
            fade = 0

            if '-f' in value:
                composite_value = value.split('-f')
                value = composite_value[0]
                fade = Util.string_to_ms(composite_value[1])

            destination_color = RGBColor(RGBColor.string_to_rgb(value))

            for led_ in led_list:
                validated_config[led_] = dict(color=destination_color,
                                              fade_ms=fade)

        return validated_config

    def process_config(self, config, **kwargs):
        # config is a validated config section:

        processed_config = dict()

        for led_name, settings_dict in config.items():
            processed_config[self.machine.leds[led_name]] = settings_dict

        return processed_config

player_cls = LedPlayer
