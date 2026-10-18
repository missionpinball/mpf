"""Format placeholder fields using segment display cell widths."""
import re

from mpf.core.placeholder_manager import MpfFormatter, TextTemplate
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText


# Width follows alignment, sign, negative-zero handling, alternate form and zero fill.
_FIELD_WIDTH = re.compile(r"((?:.[<>=^]|[<>=^])?[+\- ]?z?#?0?)([0-9]+)(.*)\Z", re.DOTALL)


class SegmentDisplayFormatter(MpfFormatter):

    """Keep integrated punctuation out of placeholder field widths."""

    __slots__ = ["_collapse_dots", "_collapse_commas", "_use_dots_for_commas"]

    # pylint: disable=too-many-arguments
    def __init__(self, machine, parameters, subscribe, collapse_dots, collapse_commas, use_dots_for_commas):
        """Initialize the formatter with the display's punctuation settings."""
        super().__init__(machine, parameters, subscribe)
        self._collapse_dots = collapse_dots
        self._collapse_commas = collapse_commas
        self._use_dots_for_commas = use_dots_for_commas

    def format_field(self, value, format_spec):
        """Increase Python's field width to compensate for integrated punctuation."""
        result = super().format_field(value, format_spec)
        match = _FIELD_WIDTH.fullmatch(format_spec)
        if match is None:
            return result

        prefix, width, suffix = match.groups()
        # Integrated punctuation used as the fill cannot add physical cells.
        if len(prefix) >= 2 and prefix[1] in "<>=^" and not SegmentDisplayText.get_display_width(
                prefix[0], self._collapse_dots, self._collapse_commas, self._use_dots_for_commas):
            return result
        requested_width = int(width)
        width = requested_width
        while True:
            visible_width = SegmentDisplayText.get_display_width(
                result, self._collapse_dots, self._collapse_commas, self._use_dots_for_commas)
            missing = requested_width - visible_width
            if missing <= 0:
                return result

            width += missing
            result = super().format_field(value, f"{prefix}{width}{suffix}")


class SegmentDisplayTextTemplate(TextTemplate):

    """Use display-aware formatting while retaining placeholder subscriptions."""

    __slots__ = ["_collapse_dots", "_collapse_commas", "_use_dots_for_commas"]

    # pylint: disable=too-many-arguments
    def __init__(self, machine, text, collapse_dots, collapse_commas, use_dots_for_commas):
        """Initialize the template with the display's punctuation settings."""
        super().__init__(machine, text)
        self._collapse_dots = collapse_dots
        self._collapse_commas = collapse_commas
        self._use_dots_for_commas = use_dots_for_commas

    def _create_formatter(self, parameters, subscribe):
        if not (self._collapse_dots or self._collapse_commas or self._use_dots_for_commas):
            return super()._create_formatter(parameters, subscribe)
        return SegmentDisplayFormatter(self.machine, parameters, subscribe, self._collapse_dots,
                                       self._collapse_commas, self._use_dots_for_commas)
