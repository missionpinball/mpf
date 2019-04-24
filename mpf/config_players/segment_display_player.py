"""Config player for text on segment displays."""
from mpf.core.delays import DelayManager

from mpf.config_players.device_config_player import DeviceConfigPlayer

MYPY = False
if MYPY:   # pragma: no cover
    from typing import Dict
    from mpf.devices.segment_display import SegmentDisplay


class SegmentDisplayPlayer(DeviceConfigPlayer):

    """Generates texts on segment displays."""

    config_file_section = 'segment_display_player'
    show_section = 'segment_displays'
    machine_collection_name = 'segment_displays'

    __slots__ = ["delay"]

    def __init__(self, machine):
        """Initialise SegmentDisplayPlayer."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine)

    def play(self, settings, context, calling_context, priority=0, **kwargs):
        """Show text on display."""
        del kwargs
        instance_dict = self._get_instance_dict(context)    # type: Dict[str, SegmentDisplay]
        full_context = self._get_full_context(context)

        for display, s in settings.items():
            action = s['action']
            if display not in instance_dict:
                instance_dict[display] = {}

            key = full_context + "." + display.name

            if s['key']:
                key += s['key']

            if action == "add":
                # add text
                display.add_text(s['text'], priority + s['priority'], key)

                if s['expire']:
                    instance_dict[display][key] = self.delay.add(
                        s['expire'], self._remove,
                        instance_dict=instance_dict,
                        key=key, display=display)
                else:
                    instance_dict[display][key] = True
            elif action == "remove":
                self._remove(instance_dict=instance_dict,
                             key=key, display=display)
            elif action == "flash":
                display.set_flashing(True)
            elif action == "no_flash":
                display.set_flashing(False)
            else:
                raise AssertionError("Invalid action {}".format(action))

    def _remove(self, instance_dict, key, display):
        if key in instance_dict[display]:
            display.remove_text_by_key(key)
            if instance_dict[display][key] is not True:
                self.delay.remove(instance_dict[display][key])
            del instance_dict[display][key]

    def clear_context(self, context):
        """Remove all texts."""
        instance_dict = self._get_instance_dict(context)
        for display, keys in instance_dict.items():
            for key in dict(keys).keys():
                self._remove(instance_dict=instance_dict,
                             key=key, display=display)

        self._reset_instance_dict(context)

    def get_express_config(self, value):
        """Parse express config."""
        return dict(action="add", text=value)
