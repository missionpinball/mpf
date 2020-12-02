"""Light config player."""
from typing import List

from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.core.rgb_color import RGBColor, ColorException
from mpf.core.utility_functions import Util


class LightPlayer(DeviceConfigPlayer):

    """Sets lights based on config."""

    config_file_section = 'light_player'
    show_section = 'lights'
    machine_collection_name = 'lights'
    allow_placeholders_in_keys = True

    __slots__ = []  # type: List[str]

    # pylint: disable-msg=too-many-locals
    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Set light color based on config."""
        key = kwargs.get("key", "")
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context + key)
        start_time = kwargs.get("start_time", None)

        for light, s in settings.items():
            final_priority = s["priority"]
            try:
                final_priority += priority
            except KeyError:
                final_priority = priority
            if isinstance(light, str):
                light_names = Util.string_to_event_list(light)
                for light_name in light_names:
                    # skip non-replaced placeholders
                    if not light_name or light_name[0:1] == "(" and light_name[-1:] == ")":
                        continue
                    self._light_named_color(light_name, instance_dict, full_context, s['color'], s["fade"],
                                            final_priority, start_time)
            else:
                self._light_color(light, instance_dict, full_context, s['color'], s["fade"], final_priority, start_time)

    def _remove(self, settings, context, key=""):
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context + key)

        for light, s in settings.items():
            if isinstance(light, str):
                light_names = Util.string_to_event_list(light)
                for light_name in light_names:
                    self._light_remove_named(light_name, instance_dict, full_context, s['fade'])
            else:
                self._light_remove(light, instance_dict, full_context, s['fade'])

    def _light_remove_named(self, light_name, instance_dict, full_context, fade_ms):
        try:
            lights = [self.machine.lights[light_name]]
        except KeyError:
            lights = self.machine.lights.items_tagged(light_name)

        for light in lights:
            self._light_remove(light, instance_dict, full_context, fade_ms)

    @staticmethod
    def _light_remove(light, instance_dict, full_context, fade_ms):
        light.remove_from_stack_by_key(full_context, fade_ms)
        try:
            del instance_dict[(full_context, light)]
        except KeyError:
            pass

    # pylint: disable-msg=too-many-arguments
    def handle_subscription_change(self, value, settings, priority, context, key):
        """Handle subscriptions."""
        if value:
            self.play(settings, context, "", priority, key=key)
        else:
            self._remove(settings, context, key=key)

    # pylint: disable-msg=too-many-arguments
    def _light_named_color(self, light_name, instance_dict,
                           full_context, color, fade_ms, priority, start_time):
        try:
            lights = [self.machine.lights[light_name]]
        except KeyError:
            lights = self.machine.lights.items_tagged(light_name)

        if not lights:
            raise AssertionError("Could not find light or tag {} in {}".format(light_name, full_context))

        for light in lights:
            self._light_color(light, instance_dict, full_context, color, fade_ms, priority, start_time)

    # pylint: disable-msg=too-many-arguments
    def _light_color(self, light, instance_dict, full_context, color, fade_ms, priority, start_time):
        if isinstance(color, str) and color == "stop":
            self._light_remove(light, instance_dict, full_context, fade_ms)
            return
        if isinstance(color, str) and color != "on":
            color = self._convert_color(color, context=light)
        light.color(color, key=full_context, fade_ms=fade_ms, priority=priority, start_time=start_time)
        instance_dict[(full_context, light)] = light

    def clear_context(self, context):
        """Remove all colors which were set in context."""
        for (full_context, _), light in self._get_instance_dict(context).items():
            light.remove_from_stack_by_key(full_context)

        self._reset_instance_dict(context)

    def _convert_color(self, color, *, context=None) -> RGBColor:
        """Convert color to RGBColor."""
        # hack to keep compatibility for matrix_light values
        if len(color) == 1:
            color = "0" + color + "0" + color + "0" + color
        elif len(color) == 2:
            color = color + color + color

        try:
            color = RGBColor(color)
        except ColorException as e:
            self.raise_config_error("Invalid color {}".format(color), 1, source_exception=e, context=context)

        return color

    def _expand_device_config(self, device_settings):
        # convert all colors to RGBColor
        device_settings = super()._expand_device_config(device_settings)
        color = device_settings['color']
        if isinstance(color, str) and "(" not in color and color not in ("on", "stop"):
            device_settings['color'] = self._convert_color(color)

        return device_settings

    def get_express_config(self, value):
        """Parse express config."""
        value = str(value).replace(' ', '')
        fade = None
        if '-f' in value:
            # Value contains both a color value and a fade value, parse it into
            # its individual components
            composite_value = value.split('-f')
            value = composite_value[0]
            fade = Util.string_to_ms(composite_value[1])

        return dict(color=value, fade=fade)
