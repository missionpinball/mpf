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
    allow_placeholders_in_keys = True

    __slots__ = []

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
                light_names = Util.string_to_list(light)
                for light_name in light_names:
                    # skip non-replaced placeholders
                    if not light_name or light_name[0:1] == "(" and light_name[-1:] == ")":
                        continue
                    self._light_named_color(light_name, instance_dict, full_context, s['color'], s["fade"],
                                            s['priority'])
            else:
                self._light_color(light, instance_dict, full_context, s['color'], s["fade"], s['priority'])

    def _remove(self, settings, context, priority):
        instance_dict = self._get_instance_dict(context)
        full_context = self._get_full_context(context)

        for light, s in settings.items():
            s = deepcopy(s)
            try:
                s['priority'] += priority
            except KeyError:
                s['priority'] = priority
            if isinstance(light, str):
                light_names = Util.string_to_list(light)
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
            del instance_dict[light.name]
        except KeyError:
            pass

    def handle_subscription_change(self, value, settings, priority, context):
        """Handle subscriptions."""
        if value:
            self.play(settings, context, "", priority)
        else:
            self._remove(settings, context, priority)

    # pylint: disable-msg=too-many-arguments
    def _light_named_color(self, light_name, instance_dict,
                           full_context, color, fade_ms, priority):
        try:
            lights = [self.machine.lights[light_name]]
        except KeyError:
            lights = self.machine.lights.items_tagged(light_name)

        if not lights:
            raise AssertionError("Could not find light or tag {} in {}".format(light_name, full_context))

        for light in lights:
            self._light_color(light, instance_dict, full_context, color, fade_ms, priority)

    # pylint: disable-msg=too-many-arguments
    def _light_color(self, light, instance_dict, full_context, color, fade_ms, priority):
        if color == "stop":
            self._light_remove(light, instance_dict, full_context, fade_ms)
            return
        if color != "on":
            # hack to keep compatibility for matrix_light values
            if len(color) == 1:
                color = "0" + color + "0" + color + "0" + color
            elif len(color) == 2:
                color = color + color + color

            color = RGBColor(color)
        light.color(color, key=full_context, fade_ms=fade_ms, priority=priority)
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
