"""LED config player."""
from mpf.core.config_player import ConfigPlayer
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util


class LedPlayer(ConfigPlayer):

    """Sets LED color based on config."""

    config_file_section = 'led_player'
    show_section = 'leds'
    machine_collection_name = "leds"

    def play(self, settings, context, priority=0, **kwargs):
        """Set LED color based on config."""
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)
        del kwargs
        if 'leds' in settings:
            settings = settings['leds']

        for led, s in settings.items():
            s['color'] = RGBColor(s['color'])
            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            try:
                led.color(key=full_context, **s)
                instance_dict[led.name] = led

            except AttributeError:
                try:
                    self._led_color(led, instance_dict, full_context, **s)
                except KeyError:
                    led_list = Util.string_to_list(led)
                    if len(led_list) > 1:
                        for led1 in led_list:
                            self._led_color(led1, instance_dict, full_context, **s)
                    else:
                        for led1 in self.machine.leds.sitems_tagged(led):
                            self._led_color(led1, instance_dict, full_context, **s)

    def _led_color(self, led_name, instance_dict, full_context, **s):
        led = self.machine.leds[led_name]
        led.color(key=full_context, **s)
        instance_dict[led.name] = led

    def clear_context(self, context):
        """Remove all colors which were set in context."""
        full_context = self._get_full_context(context)
        for led in self._get_instance_dict(context).values():
            led.remove_from_stack_by_key(full_context)

        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
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
        """Return full config."""
        super().get_full_config(value)
        value['fade_ms'] = value.pop('fade')
        return value

player_cls = LedPlayer
