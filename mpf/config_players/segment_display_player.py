"""Config player for text on segment displays."""
from mpf.core.delays import DelayManager

from mpf.config_players.device_config_player import DeviceConfigPlayer
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
from mpf.devices.segment_display.transition_manager import TransitionManager

MYPY = False
if MYPY:   # pragma: no cover
    from typing import Dict     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.segment_display.segment_display import \
        SegmentDisplay  # pylint: disable-msg=cyclic-import,unused-import


class SegmentDisplayPlayer(DeviceConfigPlayer):

    """Generates texts on segment displays."""

    config_file_section = 'segment_display_player'
    show_section = 'segment_displays'
    machine_collection_name = 'segment_displays'

    __slots__ = ["delay"]

    def __init__(self, machine):
        """initialize SegmentDisplayPlayer."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine)

    # pylint: disable=too-many-branches
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
                if key in instance_dict[display] and instance_dict[display][key] is not True:
                    self.delay.remove(instance_dict[display][key])

                # add text
                s = TransitionManager.validate_config(s, self.machine.config_validator)
                display.add_text_entry(text=s['text'],
                                       color=s['color'],
                                       flashing=self._get_flashing_type(s),
                                       flash_mask=s['flash_mask'],
                                       transition=s['transition'],
                                       transition_out=s['transition_out'],
                                       priority=priority + s['priority'],
                                       key=key)

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
                display.set_flashing(FlashingType.FLASH_ALL)
            elif action == "flash_match":
                display.set_flashing(FlashingType.FLASH_MATCH)
            elif action == "flash_mask":
                display.set_flashing(FlashingType.FLASH_MASK, s.get('flash_mask', ""))
            elif action == "no_flash":
                display.set_flashing(FlashingType.NO_FLASH)
            elif action == "set_color":
                if s['color']:
                    display.set_color(s['color'])
            else:
                raise AssertionError("Invalid action {}".format(action))

    @staticmethod
    def _get_flashing_type(config: dict):
        flashing = config.get('flashing', None)
        if flashing == "off":
            return FlashingType.NO_FLASH
        if flashing == "all":
            return FlashingType.FLASH_ALL
        if flashing == "match":
            return FlashingType.FLASH_MATCH
        if flashing == "mask":
            return FlashingType.FLASH_MASK

        return None

    def _remove(self, instance_dict, key, display):
        """Remove an instance by key."""
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
