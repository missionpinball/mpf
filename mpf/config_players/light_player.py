"""Light config player."""
from copy import deepcopy
from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util


class LightPlayer(DeviceConfigPlayer):

    """Sets lights based on config."""

    config_file_section = 'light_player'
    show_section = 'lights'
    machine_collection_name = 'lights'

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Set light color based on config."""
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)
        del kwargs

        for light, s in settings.items():
            s = deepcopy(s)
            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority
            if isinstance(light, str):
                if light in self.machine.lights:
                    self._light_named_color(light, instance_dict, full_context, **s)
                else:
                    light_list = Util.string_to_list(light)
                    if len(light_list) > 1:
                        for light1 in light_list:
                            self._light_named_color(light1, instance_dict, full_context, **s)
                    else:
                        # TODO: this case fails silently if leds do not exist
                        for light1 in self.machine.lights.items_tagged(light):
                            self._light_color(light1, instance_dict, full_context, **s)
            else:
                self._light_color(light, instance_dict, full_context, **s)

    def _light_named_color(self, light_name, instance_dict, full_context, color, **s):
        light = self.machine.lights[light_name]
        self._light_color(light, instance_dict, full_context, color, **s)

    @staticmethod
    def _light_color(light, instance_dict, full_context, color, **s):
        if color == "on":
            color = light.config['default_on_color']
        else:
            # hack to keep compatibility for matrix_light values
            if len(color) == 1:
                color = "0" + color + "0" + color + "0" + color
            elif len(color) == 2:
                color = color + color + color

            color = RGBColor(color)
        light.color(color, key=full_context, **s)
        instance_dict[light.name] = light

    def clear_context(self, context):
        """Remove all colors which were set in context."""
        full_context = self._get_full_context(context)
        for light in self._get_instance_dict(context).values():
            light.remove_from_stack_by_key(full_context)

        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        value = str(value).replace(' ', '').lower()
        fade = None
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

player_cls = LightPlayer
