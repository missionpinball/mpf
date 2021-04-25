"""Physical segment displays."""
from collections import OrderedDict
from typing import Optional, Dict, List

from mpf.core.clock import PeriodicTask
from mpf.core.rgb_color import RGBColor
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.placeholder_manager import TextTemplate
from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText
from mpf.devices.segment_display.text_stack_entry import TextStackEntry
from mpf.devices.segment_display.transition_manager import TransitionManager
from mpf.devices.segment_display.transitions import TransitionRunner, TransitionBase
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
from mpf.plugins.virtual_segment_display_connector import VirtualSegmentDisplayConnector

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface     # pylint: disable-msg=cyclic-import,unused-import; # noqa
    from mpf.core.platform import SegmentDisplayPlatform    # pylint: disable-msg=cyclic-import,unused-import; # noqa


# pylint: disable=too-many-instance-attributes
@DeviceMonitor("text")
class SegmentDisplay(SystemWideDevice):

    """A physical segment display in a pinball machine."""

    config_section = 'segment_displays'
    collection = 'segment_displays'
    class_label = 'segment_display'
    transition_manager = None
    empty_text_stack_entry = TextStackEntry("", None, FlashingType.NO_FLASH, "",
                                            None, None, -999999, "__empty__")

    def __init__(self, machine, name: str) -> None:
        """Initialise segment display device."""
        super().__init__(machine, name)
        if not self.transition_manager:
            self.transition_manager = TransitionManager(machine)

        self.hw_display = None                      # type: Optional[SegmentDisplayPlatformInterface]
        self.platform = None                        # type: Optional[SegmentDisplayPlatform]
        self.size = 7                               # type: int
        self.integrated_dots = False                # type: bool
        self.integrated_commas = False              # type: bool
        self.default_transition_update_hz = 30.0    # type: float
        self.text = ""                              # type: Optional[str]
        self.colors = []                            # type: List[RGBColor]
        self.flashing = FlashingType.NO_FLASH       # type: FlashingType
        self.flash_mask = ""                        # type: Optional[str]
        self.platform_options = None                # type: Optional[dict]
        self.virtual_connector = None               # type: Optional[VirtualSegmentDisplayConnector]
        self._text_stack = {}                       # type: Dict[str:TextStackEntry]
        self._current_placeholder = None            # type: Optional[TextTemplate]
        self._current_text_stack_entry = None       # type: Optional[TextStackEntry]
        self._transition_update_task = None         # type: Optional[PeriodicTask]
        self._current_transition = None             # type: Optional[TransitionRunner]

    async def _initialize(self):
        """Initialise display."""
        await super()._initialize()
        # load platform
        self.platform = self.machine.get_platform_sections('segment_displays', self.config['platform'])
        self.platform.assert_has_feature("segment_displays")

        if not self.platform.features['allow_empty_numbers'] and self.config['number'] is None:
            self.raise_config_error("Segment Display must have a number.", 1)

        self.size = self.config['size']
        self.integrated_dots = self.config['integrated_dots']
        self.integrated_commas = self.config['integrated_commas']
        self.default_transition_update_hz = self.config['default_transition_update_hz']

        # configure hardware
        try:
            self.hw_display = await self.platform.configure_segment_display(self.config['number'],
                                                                            self.config['platform_settings'])
        except AssertionError as ex:
            raise AssertionError("Error in platform while configuring segment display {}. "
                                 "See error above.".format(self.name)) from ex

        self.set_color(self.config['initial_color'])

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

    def add_text_entry(self, text_stack_entry: TextStackEntry):
        """Add text to display stack.

        This will replace texts with the same key.
        """
        # remove old text in case it has the same key
        self._text_stack[text_stack_entry.key] = text_stack_entry
        self._update_stack()

    def add_text(self, text: str, priority: int = 0, key: str = None) -> None:
        """Add text to display stack.

        This will replace texts with the same key.
        """
        self.add_text_entry(TextStackEntry(text, None, None, None, None, None, priority, key))

    def set_flashing(self, flashing: FlashingType, flash_mask: str = ""):
        """Enable/Disable flashing."""
        self.flashing = flashing
        self.flash_mask = flash_mask
        self._update_display(self.text)

    def set_color(self, colors: List[RGBColor]):
        """Set display colors."""
        if not isinstance(colors, list):
            colors = [colors]
        self.colors = colors
        assert self.hw_display is not None
        self.hw_display.set_color(colors)
        if self.virtual_connector:
            self.virtual_connector.set_color(self.name, colors)

    def remove_text_by_key(self, key: Optional[str] = None):
        """Remove entry from text stack."""
        if key in self._text_stack:
            del self._text_stack[key]
            if not self._text_stack:
                self.add_text_entry(self.empty_text_stack_entry)
            else:
                self._update_stack()

    # pylint: disable=too-many-arguments
    def _start_transition(self, transition: TransitionBase, current_text: str, new_text: str,
                          current_colors: Optional[List[RGBColor]] = None, new_colors: Optional[List[RGBColor]] = None,
                          update_hz: float = 30.0):
        """Start the specified transition."""
        if self._current_transition:
            self._stop_transition()
        self._current_transition = TransitionRunner(self.machine, transition, current_text, new_text,
                                                    current_colors, new_colors)
        transition_text = next(self._current_transition)
        transition_colors = SegmentDisplayText.get_colors(transition_text)
        self._update_display(SegmentDisplayText.convert_to_str(transition_text), transition_colors)
        self._transition_update_task = self.machine.clock.schedule_interval(self._update_transition, 1 / update_hz)

    def _update_transition(self):
        """Update the current transition (callback function from transition interval clock)."""
        try:
            transition_text = next(self._current_transition)
            transition_colors = SegmentDisplayText.get_colors(transition_text)
            self._update_display(SegmentDisplayText.convert_to_str(transition_text), transition_colors)

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
                # update colors
                if self._current_text_stack_entry.colors:
                    self.colors = self._current_text_stack_entry.colors

                # update placeholder
                if len(self._current_text_stack_entry.text) > 0:
                    self._current_placeholder = TextTemplate(self.machine, self._current_text_stack_entry.text)
                    self._current_placeholder_changed()
            else:
                self._current_placeholder = None

    def _update_stack(self) -> None:
        """Sort stack and show top entry on display."""
        # do nothing if stack is emtpy. set display empty
        assert self.hw_display is not None
        if not self._text_stack:
            self._current_text_stack_entry = None
            self._stop_transition()

            if self._current_placeholder:
                self.text = ""
                self._current_placeholder = None

            self.hw_display.set_text("", flashing=FlashingType.NO_FLASH)
            return

        # sort text stack by priority
        self._text_stack = OrderedDict(
            sorted(self._text_stack.items(), key=lambda item: item[1].priority, reverse=True))

        # get top entry (highest priority)
        top_text_stack_entry = next(iter(self._text_stack.values()))
        previous_text_stack_entry = self._current_text_stack_entry
        self._current_text_stack_entry = top_text_stack_entry

        # determine if the new key is different than the previous key (out transitions are only applied
        # when changing keys)
        transition_config = None
        if previous_text_stack_entry and top_text_stack_entry.key != previous_text_stack_entry.key:
            if previous_text_stack_entry.transition_out:
                transition_config = previous_text_stack_entry.transition_out

        # determine if new text entry has a transition, if so, apply it (overrides any outgoing transition)
        if top_text_stack_entry.transition:
            transition_config = top_text_stack_entry.transition

        # start transition (if configured)
        if transition_config:
            transition = self.transition_manager.get_transition(self.size,
                                                                self.integrated_dots,
                                                                self.integrated_commas,
                                                                transition_config)
            if previous_text_stack_entry:
                previous_text = previous_text_stack_entry.text
            else:
                previous_text = ""

            self._start_transition(transition, previous_text, top_text_stack_entry.text,
                                   self.colors, top_text_stack_entry.colors,
                                   self.default_transition_update_hz)
        else:
            # no transition - subscribe to text template changes and update display
            self._current_placeholder = TextTemplate(self.machine, top_text_stack_entry.text)
            new_text, future = self._current_placeholder.evaluate_and_subscribe({})
            future.add_done_callback(self._current_placeholder_changed)

            # set any flashing state specified in the entry
            if top_text_stack_entry.flashing is not None:
                self.flashing = top_text_stack_entry.flashing
                self.flash_mask = top_text_stack_entry.flash_mask

            # update colors if specified
            if top_text_stack_entry.colors:
                self.colors = top_text_stack_entry.colors

            # update the display
            self._update_display(new_text, top_text_stack_entry.colors)

    def _current_placeholder_changed(self, *args, **kwargs) -> None:
        """Update display when a placeholder changes (callback function)."""
        del args
        del kwargs
        new_text, future = self._current_placeholder.evaluate_and_subscribe({})
        future.add_done_callback(self._current_placeholder_changed)
        self._update_display(new_text)

    def _update_display(self, new_text: str, new_colors: Optional[List[RGBColor]] = None) -> None:
        """Update display to current text."""
        assert self.hw_display is not None

        # set text to display
        self.text = new_text
        self.hw_display.set_text(self.text, flashing=self.flashing, flash_mask=self.flash_mask, colors=new_colors)
        if self.virtual_connector:
            self.virtual_connector.set_text(self.name, self.text, flashing=self.flashing,
                                            flash_mask=self.flash_mask, colors=new_colors)
