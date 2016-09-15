"""LED config player."""
from copy import deepcopy
from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util


class LedPlayer(DeviceConfigPlayer):

    """Sets LED color based on config."""

    config_file_section = 'led_player'
    show_section = 'leds'
    machine_collection_name = "leds"

    def play(self, settings, context, priority=0, **kwargs):
        """Set LED color based on config."""
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)
        del kwargs

        for led, s in settings.items():
            s = deepcopy(s)
            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority

            try:
                self._led_color(led, instance_dict, full_context, **s)

            except AttributeError:
                try:
                    self._led_named_color(led, instance_dict, full_context, **s)
                except KeyError:
                    led_list = Util.string_to_list(led)
                    if len(led_list) > 1:
                        for led1 in led_list:
                            self._led_named_color(led1, instance_dict, full_context, **s)
                    else:
                        for led1 in self.machine.leds.sitems_tagged(led):
                            self._led_named_color(led1, instance_dict, full_context, **s)

    def _led_named_color(self, led_name, instance_dict, full_context, color, **s):
        led = self.machine.leds[led_name]
        self._led_color(led, instance_dict, full_context, color, **s)

    @staticmethod
    def _led_color(led, instance_dict, full_context, color, **s):
        if color == "on":
            color = led.config['default_color']
        else:
            color = RGBColor(color)
        led.color(color, key=full_context, **s)
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
            # Value contains both a color value and a fade value, parse it into
            # its individual components
            composite_value = value.split('-f')
            value = composite_value[0]
            fade = Util.string_to_ms(composite_value[1])

        return dict(color=value, fade=fade)

    def get_full_config(self, value):
        """Return full config."""
        super().get_full_config(value)
        value['fade_ms'] = value.pop('fade')
        return value

player_cls = LedPlayer
