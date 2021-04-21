"""Physical segment displays."""
from collections import namedtuple, OrderedDict
from typing import Optional, Dict

from mpf.core.rgb_color import RGBColor
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.placeholder_manager import TextTemplate
from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.segment_display.text_stack_entry import TextStackEntry
from mpf.devices.segment_display.transition_manager import TransitionManager
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
from mpf.plugins.virtual_segment_display_connector import VirtualSegmentDisplayConnector

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface     # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.core.platform import SegmentDisplayPlatform    # pylint: disable-msg=cyclic-import,unused-import; # noqa


@DeviceMonitor("text")
class SegmentDisplay(SystemWideDevice):

    """A physical segment display in a pinball machine."""

    config_section = 'segment_displays'
    collection = 'segment_displays'
    class_label = 'segment_display'
    transition_manager = None

    def __init__(self, machine, name: str) -> None:
        """Initialise segment display device."""
        super().__init__(machine, name)
        if not self.transition_manager:
            self.transition_manager = TransitionManager(machine)

        self.hw_display = None                  # type: Optional[SegmentDisplayPlatformInterface]
        self.platform = None                    # type: Optional[SegmentDisplayPlatform]
        self._text_stack = {}                   # type: Dict[str:TextStackEntry]
        self._current_placeholder = None        # type: Optional[TextTemplate]
        self.text = ""                          # type: Optional[str]
        self.color = None                       # type: Optional[RGBColor]
        self._current_text_stack = None          # type: Optional[TextStackEntry]
        self.flashing = FlashingType.NO_FLASH   # type: FlashingType
        self.flash_mask = ""                    # type: Optional[str]
        self.platform_options = None            # type: Optional[dict]
        self.virtual_connector = None           # type: Optional[VirtualSegmentDisplayConnector]
        self._transition_update_task = None
        self._current_transition = None
        self._current_transition_step = 0

    async def _initialize(self):
        """Initialise display."""
        await super()._initialize()
        # load platform
        self.platform = self.machine.get_platform_sections('segment_displays', self.config['platform'])
        self.platform.assert_has_feature("segment_displays")

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Segment Display must have a number.", 1)

        # configure hardware
        try:
            self.hw_display = await self.platform.configure_segment_display(self.config['number'],
                                                                            self.config['platform_settings'])
        except AssertionError as e:
            raise AssertionError("Error in platform while configuring segment display {}. "
                                 "See error above.".format(self.name)) from e

    def add_virtual_connector(self, virtual_connector):
        """Add a virtual connector instance to connect this segment display to the MPF-MC for virtual displays."""
        self.virtual_connector = virtual_connector

    def remove_virtual_connector(self):
        """Remove the virtual connector instance from this segment display."""
        self.virtual_connector = None

    def validate_and_parse_config(self, config: dict, is_mode_config: bool, debug_prefix: str = None) -> dict:
        """Return the parsed and validated config.

        Args:
        ----
            config: Config of device
            is_mode_config: Whether this device is loaded in a mode or system-wide
            debug_prefix: Prefix to use when logging.

        Returns: Validated config
        """
        config = super().validate_and_parse_config(config, is_mode_config, debug_prefix)
        platform = self.machine.get_platform_sections('segment_displays', getattr(config, "platform", None))
        platform.assert_has_feature("segment_displays")
        config['platform_settings'] = platform.validate_segment_display_section(self,
                                                                                config.get('platform_settings', None))
        return config

    def add_text(self, text_stack_entry: TextStackEntry) -> None:
        """Add text to display stack.

        This will replace texts with the same key.
        """
        # remove old text in case it has the same key
        self._text_stack[text_stack_entry.key] = text_stack_entry
        self._update_stack()

    def set_flashing(self, flashing: FlashingType, flash_mask: str = ""):
        """Enable/Disable flashing."""
        self.flashing = flashing
        self.flash_mask = flash_mask
        # invalidate text to force an update
        self.text = None
        self._update_display()

    def set_color(self, color: RGBColor):
        """Set display color."""
        self.color = color
        assert self.hw_display is not None
        self.hw_display.set_color(color)
        if self.virtual_connector:
            self.virtual_connector.set_color(self.name, self.color)

    def remove_text_by_key(self, key: str):
        """Remove entry from text stack."""
        self._text_stack[:] = [x for x in self._text_stack if x.key != key]
        self._update_stack()

    def _start_transition(self):
        if self._transition_update_task:
            self._stop_transition()

        self._current_transition_step = 0
        self._transition_update_task = self.machine.clock.schedule_interval(self._update_transition, 1 / 30.0)

    def _update_transition(self):

        self._current_transition_step += 1

    def _stop_transition(self):
        if self._transition_update_task:
            self._transition_update_task.cancel()
            self._transition_update_task = None

        self._current_placeholder = TextTemplate(self.machine, self._.text)


    def _update_stack(self) -> None:
        """Sort stack and show top entry on display."""
        # do nothing if stack is emtpy. set display empty
        assert self.hw_display is not None
        if not self._text_stack:
            self.hw_display.set_text("", flashing=FlashingType.NO_FLASH)
            if self._current_placeholder:
                self.text = ""
                self._current_placeholder = None
            return

        # sort stack by priority
        self._text_stack = OrderedDict(
            sorted(self._text_stack.items(), key=lambda item: item[1].priority))

        # get top entry (highest priority)
        _, top_text_stack_entry = self._text_stack.popitem()

        # determine if the new key is different than the previous key (out transitions are only applied
        # when changing keys)
        transition_config = None
        if self._previous_text_stack_entry and top_text_stack_entry.key != self._previous_text_stack_entry.key:
            if self._previous_text_stack_entry.transition_out:
                transition_config = self._previous_text_stack_entry.transition_out
        if top_text_stack_entry.transition:
            transition_config = top_text_stack_entry.transition

        self._previous_text_stack_entry = self._current_text_stack_entry

        if transition_config:
            # start transition
            transition = self.transition_manager.get_transition(self.text,
                                                                self.machine.
                                                                transition_config)
            if transition:
                self._current_transition_steps = transition.transition_steps
                self._start_transition()
            else:
                self._current_transition_steps = None

        self._update_display()

    def _update_display(self, *args, **kwargs) -> None:
        """Update display to current text."""
        del args
        del kwargs
        assert self.hw_display is not None
        if not self._current_placeholder:
            new_text = ""
        else:
            new_text, future = self._current_placeholder.evaluate_and_subscribe({})
            future.add_done_callback(self._update_display)

        # set text to display if it changed
        if new_text != self.text:
            self.text = new_text
            self.hw_display.set_text(self.text, flashing=self.flashing, flash_mask=self.flash_mask)
            if self.virtual_connector:
                self.virtual_connector.set_text(self.name, self.text, flashing=self.flashing,
                                                flash_mask=self.flash_mask)
