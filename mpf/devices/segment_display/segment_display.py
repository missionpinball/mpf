"""Physical segment displays."""
from asyncio import Future
from typing import Optional, Dict, List

from mpf.core.clock import PeriodicTask
from mpf.core.rgb_color import RGBColor
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.placeholder_manager import TextTemplate
from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.segment_display.text_stack_entry import TextStackEntry
from mpf.devices.segment_display.transition_manager import TransitionManager
from mpf.devices.segment_display.transitions import TransitionRunner, TransitionBase
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText, ColoredSegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
from mpf.plugins.virtual_segment_display_connector import VirtualSegmentDisplayConnector

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface     # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.core.platform import SegmentDisplayPlatform    # pylint: disable-msg=cyclic-import,unused-import; # noqa


class SegmentDisplayState:

    """Current State."""

    __slots__ = ["text", "flashing", "flash_mask"]

    def __init__(self, text: ColoredSegmentDisplayText, flashing: FlashingType, flash_mask: Optional[str] = None):
        """Class initializer."""
        self.text = text
        self.flashing = flashing
        self.flash_mask = flash_mask

    def __repr__(self):
        """Return str representation."""
        return '<TextStackEntry: {} (flashing: {} flashing_mask: {}) >'.format(
            self.text, self.flashing, self.flash_mask)

    def __eq__(self, other):
        """Compose two instances."""
        return self.text == other.text and self.flashing == other.flashing and \
            self.flash_mask == other.flash_mask


# pylint: disable=too-many-instance-attributes
@DeviceMonitor("text")
class SegmentDisplay(SystemWideDevice):

    """A physical segment display in a pinball machine."""

    __slots__ = ["hw_display", "size", "virtual_connector", "_text_stack", "_current_placeholder",
                 "_current_text_stack_entry", "_transition_update_task", "_current_transition", "_default_color",
                 "_current_state", "_current_placeholder_future"]

    config_section = 'segment_displays'
    collection = 'segment_displays'
    class_label = 'segment_display'

    def __init__(self, machine, name: str) -> None:
        """initialize segment display device."""
        super().__init__(machine, name)
        self.hw_display = None                      # type: Optional[SegmentDisplayPlatformInterface]
        self.platform = None                        # type: Optional[SegmentDisplayPlatform]
        self.size = None                            # type: Optional[int]

        self.virtual_connector = None               # type: Optional[VirtualSegmentDisplayConnector]
        self._text_stack = {}                       # type: Dict[str, TextStackEntry]
        self._current_placeholder = None            # type: Optional[TextTemplate]
        self._current_placeholder_future = None     # type: Optional[Future]
        self._current_text_stack_entry = None       # type: Optional[TextStackEntry]
        self._transition_update_task = None         # type: Optional[PeriodicTask]
        self._current_transition = None             # type: Optional[TransitionRunner]
        self._default_color = None                  # type: Optional[RGBColor]
        self._current_state = None                  # type: Optional[SegmentDisplayState]

    async def _initialize(self):
        """initialize display."""
        await super()._initialize()
        # load platform
        self.platform = self.machine.get_platform_sections('segment_displays', self.config['platform'])
        self.platform.assert_has_feature("segment_displays")

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Segment Display must have a number.", 1)

        self.size = self.config['size']
        self._default_color = [RGBColor(color) for color in self.config["default_color"][0:self.size]]
        if len(self._default_color) < self.size:
            self._default_color += [RGBColor("white")] * (self.size - len(self._default_color))

        # configure hardware
        try:
            self.hw_display = await self.platform.configure_segment_display(self.config['number'],
                                                                            self.size,
                                                                            self.config['platform_settings'])
        except AssertionError as ex:
            raise AssertionError("Error in platform while configuring segment display {}. "
                                 "See error above.".format(self.name)) from ex

        text = SegmentDisplayText.from_str("", self.size, self.config['integrated_dots'],
                                           self.config['integrated_commas'], self.config['use_dots_for_commas'],
                                           self._default_color)
        self._update_display(SegmentDisplayState(text, FlashingType.NO_FLASH, ''))

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
        platform = self.machine.get_platform_sections('segment_displays', config.get("platform", None))
        platform.assert_has_feature("segment_displays")
        config['platform_settings'] = platform.validate_segment_display_section(self,
                                                                                config.get('platform_settings', None))
        return config

    # pylint: disable-msg=too-many-arguments
    def add_text_entry(self, text, color, flashing, flash_mask, transition, transition_out, priority, key):
        """Add text to display stack.

        This will replace texts with the same key.
        """
        # remove old text in case it has the same key
        self._text_stack[key] = TextStackEntry(
            text, color, flashing, flash_mask, transition, transition_out, priority, key)
        self._update_stack()

    def add_text(self, text: str, priority: int = 0, key: str = None) -> None:
        """Add text to display stack.

        This will replace texts with the same key.
        """
        self.add_text_entry(text, None, None, None, None, None, priority, key)

    def remove_text_by_key(self, key: Optional[str]):
        """Remove entry from text stack."""
        if key in self._text_stack:
            del self._text_stack[key]
            self._update_stack()

    # pylint: disable=too-many-arguments
    def _start_transition(self, transition: TransitionBase, current_text: str, new_text: str,
                          current_colors: List[RGBColor], new_colors: List[RGBColor],
                          update_hz: float, flashing, flash_mask):
        """Start the specified transition."""
        current_colors = self._expand_colors(current_colors, len(current_text))
        new_colors = self._expand_colors(new_colors, len(new_text))
        if self._current_transition:
            self._stop_transition()
        self._current_transition = TransitionRunner(self.machine, transition, current_text, new_text,
                                                    current_colors, new_colors)
        transition_text = next(self._current_transition)
        self._update_display(SegmentDisplayState(transition_text, flashing, flash_mask))
        self._transition_update_task = self.machine.clock.schedule_interval(self._update_transition, 1 / update_hz)

    def _update_transition(self):
        """Update the current transition (callback function from transition interval clock)."""
        try:
            transition_text = next(self._current_transition)
            self._update_display(SegmentDisplayState(transition_text, self._current_state.flashing,
                                                     self._current_state.flash_mask))

        except StopIteration:
            self._stop_transition()

    def _stop_transition(self):
        """Stop the current transition."""
        if self._transition_update_task:
            self._transition_update_task.cancel()
            self._transition_update_task = None

        if self._current_transition:
            self._current_transition = None

            if self._current_text_stack_entry:
                # update placeholder
                if len(self._current_text_stack_entry.text) > 0:
                    self._current_placeholder = TextTemplate(self.machine, self._current_text_stack_entry.text)
                    self._current_placeholder_changed()
            else:
                self._current_placeholder = None

    def _expand_colors(self, colors, length):
        """Expand color to a certain length."""
        if not colors:
            colors = self._default_color
        if len(colors) > length:
            colors = colors[0:length]
        elif len(colors) < length:
            colors = colors + [colors[len(colors) - 1]] * (length - len(colors))

        return colors

    def _update_stack(self) -> None:
        """Sort stack and show top entry on display."""
        # do nothing if stack is emtpy. set display empty
        assert self.hw_display is not None
        if not self._text_stack:
            top_text_stack_entry = TextStackEntry(" " * self.size, None, FlashingType.NO_FLASH, "", None, None,
                                                  -999999, "")
        else:
            # sort text stack by priority
            self._text_stack = dict(
                sorted(self._text_stack.items(), key=lambda item: item[1].priority, reverse=True))

            # get top entry (highest priority)
            top_text_stack_entry = next(iter(self._text_stack.values()))

        previous_text_stack_entry = self._current_text_stack_entry
        self._current_text_stack_entry = top_text_stack_entry

        # determine if the new key is different than the previous key (out transitions are only applied
        # when changing keys)
        transition_config = None
        if previous_text_stack_entry and top_text_stack_entry.key != previous_text_stack_entry.key and \
                previous_text_stack_entry.transition_out:
            transition_config = previous_text_stack_entry.transition_out

        # determine if new text entry has a transition, if so, apply it (overrides any outgoing transition)
        if top_text_stack_entry.transition:
            transition_config = top_text_stack_entry.transition

        # start transition (if configured)
        if transition_config:
            transition = TransitionManager.get_transition(self.size,
                                                          self.config['integrated_dots'],
                                                          self.config['integrated_commas'],
                                                          self.config['use_dots_for_commas'],
                                                          transition_config)
            if previous_text_stack_entry:
                previous_text = previous_text_stack_entry.text
            else:
                previous_text = " " * self.size

            if top_text_stack_entry.flashing is not None:
                flashing = top_text_stack_entry.flashing
                flash_mask = top_text_stack_entry.flash_mask
            else:
                flashing = self._current_state.flashing
                flash_mask = self._current_state.flash_mask

            self._start_transition(transition, previous_text, top_text_stack_entry.text,
                                   self._current_state.text.get_colors(), top_text_stack_entry.colors,
                                   self.config['default_transition_update_hz'], flashing, flash_mask)
        else:
            # no transition - subscribe to text template changes and update display
            self._current_placeholder = TextTemplate(self.machine, top_text_stack_entry.text)
            new_text, future = self._current_placeholder.evaluate_and_subscribe({})
            future.add_done_callback(self._current_placeholder_changed)

            # set any flashing state specified in the entry
            if top_text_stack_entry.flashing is not None:
                flashing = top_text_stack_entry.flashing
                flash_mask = top_text_stack_entry.flash_mask
            else:
                flashing = self._current_state.flashing
                flash_mask = self._current_state.flash_mask

            # update colors if specified
            if top_text_stack_entry.colors:
                colors = top_text_stack_entry.colors
            else:
                colors = self._current_state.text.get_colors()

            # update the display
            text = SegmentDisplayText.from_str(new_text, self.size, self.config['integrated_dots'],
                                               self.config['integrated_commas'], self.config['use_dots_for_commas'],
                                               colors)
            self._update_display(SegmentDisplayState(text, flashing, flash_mask))

    def _current_placeholder_changed(self, future=None, **kwargs) -> None:
        """Update display when a placeholder changes (callback function)."""
        del kwargs
        if future and future.cancelled():
            return
        if self._current_placeholder_future and not self._current_placeholder_future.done():
            self._current_placeholder_future.cancel()
        new_text, self._current_placeholder_future = self._current_placeholder.evaluate_and_subscribe({})
        self._current_placeholder_future.add_done_callback(self._current_placeholder_changed)
        text = SegmentDisplayText.from_str(new_text, self.size, self.config['integrated_dots'],
                                           self.config['integrated_commas'], self.config['use_dots_for_commas'],
                                           self._current_state.text.get_colors())
        self._update_display(SegmentDisplayState(text, self._current_state.flashing,
                                                 self._current_state.flash_mask))

    def set_flashing(self, flashing: FlashingType, flash_mask: str = ""):
        """Enable/Disable flashing."""
        self._update_display(SegmentDisplayState(self._current_state.text, flashing, flash_mask))

    def set_color(self, colors: List[RGBColor]):
        """Set display colors."""
        assert isinstance(colors, list)
        assert self.hw_display is not None
        text = SegmentDisplayText.from_str(self._current_state.text.convert_to_str(), self.size,
                                           self.config['integrated_dots'], self.config['integrated_commas'],
                                           self.config['use_dots_for_commas'], colors)
        self._update_display(SegmentDisplayState(text,
                                                 self._current_state.flashing,
                                                 self._current_state.flash_mask))

    @property
    def text(self):
        """Return current text."""
        return self._current_state.text.convert_to_str()

    @property
    def colors(self):
        """Return current colors."""
        return self._current_state.text.get_colors()

    @property
    def flashing(self):
        """Return current flashing state."""
        return self._current_state.flashing

    @property
    def flash_mask(self):
        """Return current flash mask."""
        return self._current_state.flash_mask

    def _update_display(self, new_state: SegmentDisplayState) -> None:
        """Update display to current text."""
        assert self.hw_display is not None
        if self._current_state and new_state == self._current_state:
            return

        self._current_state = new_state
        text = new_state.text
        flashing = new_state.flashing
        flash_mask = new_state.flash_mask

        assert len(text) == self.size

        # set text to display
        self.hw_display.set_text(text, flashing=flashing, flash_mask=flash_mask)
        if self.virtual_connector:
            self.virtual_connector.set_text(self.name, text, flashing=flashing, flash_mask=flash_mask)
