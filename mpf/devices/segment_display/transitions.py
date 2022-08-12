"""Text transitions used for segment displays."""
import abc
from typing import Optional, List

from mpf.core.placeholder_manager import TextTemplate
from mpf.core.rgb_color import RGBColor
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText, UncoloredSegmentDisplayText

STEP_OUT_OF_RANGE_ERROR = "Step is out of range"
TRANSITION_DIRECTION_UNKNOWN_ERROR = "Transition uses an unknown direction value"


class TransitionBase(metaclass=abc.ABCMeta):

    """Base class for text transitions in segment displays."""

    __slots__ = ["output_length", "config", "collapse_dots", "collapse_commas", "use_dots_for_commas"]

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool, config: dict) -> None:
        """Initialize the transition."""
        self.output_length = output_length
        self.config = config
        self.collapse_dots = collapse_dots
        self.collapse_commas = collapse_commas
        self.use_dots_for_commas = use_dots_for_commas

        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @abc.abstractmethod
    def get_step_count(self):
        """Return the total number of steps required for the transition."""
        raise NotImplementedError

    # pylint: disable=too-many-arguments
    @abc.abstractmethod
    def get_transition_step(self, step: int, current_text: str, new_text: str,
                            current_colors: Optional[List[RGBColor]] = None,
                            new_colors: Optional[List[RGBColor]] = None) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        raise NotImplementedError


class TransitionRunner:

    """Class to run/execute transitions using an iterator."""

    __slots__ = ["_transition", "_step", "_current_placeholder", "_new_placeholder", "_current_colors", "_new_colors"]

    # pylint: disable=too-many-arguments
    def __init__(self, machine, transition: TransitionBase, current_text: str, new_text: str,
                 current_colors: Optional[List[RGBColor]] = None,
                 new_colors: Optional[List[RGBColor]] = None) -> None:
        """Class initializer."""
        self._transition = transition
        self._step = 0
        self._current_placeholder = TextTemplate(machine, current_text)
        self._new_placeholder = TextTemplate(machine, new_text)
        self._current_colors = current_colors
        self._new_colors = new_colors

    def __iter__(self):
        """Return the iterator."""
        return self

    def __next__(self):
        """Evaluate and return the next transition step."""
        if self._step >= self._transition.get_step_count():
            raise StopIteration

        transition_step = self._transition.get_transition_step(self._step,
                                                               self._current_placeholder.evaluate({}),
                                                               self._new_placeholder.evaluate({}),
                                                               self._current_colors,
                                                               self._new_colors)
        self._step += 1
        return transition_step


class NoTransition(TransitionBase):

    """Segment display no transition effect."""

    def get_step_count(self):
        """Return the total number of steps required for the transition."""
        return 1

    # pylint: disable=too-many-arguments
    def get_transition_step(self, step: int, current_text: str, new_text: str,
                            current_colors: Optional[List[RGBColor]] = None,
                            new_colors: Optional[List[RGBColor]] = None) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError(STEP_OUT_OF_RANGE_ERROR)

        return SegmentDisplayText.from_str(new_text, self.output_length, self.collapse_dots, self.collapse_commas,
                                           self.use_dots_for_commas, new_colors)


class PushTransition(TransitionBase):

    """Segment display push transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool, 
                 config: dict) -> None:
        """Class initializer."""
        self.direction = 'right'
        self.text = None
        self.text_color = None
        super().__init__(output_length, collapse_dots, collapse_commas, use_dots_for_commas, config)

        if self.text is None:
            self.text = ''

    def get_step_count(self):
        """Return the total number of steps required for the transition."""
        return self.output_length + len(self.text)

    # pylint: disable=too-many-arguments
    def get_transition_step(self, step: int, current_text: str, new_text: str,
                            current_colors: Optional[List[RGBColor]] = None,
                            new_colors: Optional[List[RGBColor]] = None) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError(STEP_OUT_OF_RANGE_ERROR)

        current_display_text = SegmentDisplayText.from_str(current_text, self.output_length, self.collapse_dots,
                                                           self.collapse_commas, self.use_dots_for_commas, 
                                                           current_colors)
        new_display_text = SegmentDisplayText.from_str(new_text, self.output_length, self.collapse_dots,
                                                       self.collapse_commas, self.use_dots_for_commas, new_colors)

        if self.text:
            if new_colors and not self.text_color:
                text_color = [new_colors[0]]
            else:
                text_color = self.text_color
            transition_text = SegmentDisplayText.from_str(self.text, len(self.text), self.collapse_dots,
                                                          self.collapse_commas, self.use_dots_for_commas, text_color)
        else:
            transition_text = UncoloredSegmentDisplayText([], self.collapse_dots, self.collapse_commas, 
                                                          self.use_dots_for_commas)

        if self.direction == 'right':
            temp_list = new_display_text
            temp_list.extend(transition_text)
            temp_list.extend(current_display_text)
            return temp_list[
                self.output_length + len(self.text) - (step + 1):2 * self.output_length + len(
                    self.text) - (step + 1)]

        if self.direction == 'left':
            temp_list = current_display_text
            temp_list.extend(transition_text)
            temp_list.extend(new_display_text)
            return temp_list[step + 1:step + 1 + self.output_length]

        raise AssertionError(TRANSITION_DIRECTION_UNKNOWN_ERROR)


class CoverTransition(TransitionBase):

    """Segment display cover transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool,
                 config: dict) -> None:
        """Class initializer."""
        self.direction = 'right'
        self.text = None
        self.text_color = None
        super().__init__(output_length, collapse_dots, collapse_commas, use_dots_for_commas, config)

        if self.text is None:
            self.text = ''

    def get_step_count(self):
        """Return the total number of steps required for the transition."""
        return self.output_length + len(self.text)

    # pylint: disable=too-many-arguments
    def get_transition_step(self, step: int, current_text: str, new_text: str,
                            current_colors: Optional[List[RGBColor]] = None,
                            new_colors: Optional[List[RGBColor]] = None) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError(STEP_OUT_OF_RANGE_ERROR)

        current_display_text = SegmentDisplayText.from_str(current_text, self.output_length, self.collapse_dots,
                                                           self.collapse_commas, self.use_dots_for_commas, 
                                                           current_colors)
        new_display_text = SegmentDisplayText.from_str(new_text, self.output_length, self.collapse_dots,
                                                       self.collapse_commas, self.use_dots_for_commas, new_colors)

        if self.text:
            if new_colors and not self.text_color:
                text_color = [new_colors[0]]
            else:
                text_color = self.text_color
            transition_text = SegmentDisplayText.from_str(self.text, len(self.text), self.collapse_dots,
                                                          self.collapse_commas, self.use_dots_for_commas, text_color)
        else:
            transition_text = UncoloredSegmentDisplayText([], self.collapse_dots, self.collapse_commas, 
                                                          self.use_dots_for_commas,)

        if self.direction == 'right':
            new_extended_display_text = new_display_text
            new_extended_display_text.extend(transition_text)

            if step < self.output_length:
                temp_text = new_extended_display_text[-(step + 1):]
                temp_text.extend(current_display_text[step + 1:])
            else:
                temp_text = new_display_text[-(step + 1):-(step + 1) + self.output_length]

            return temp_text

        if self.direction == 'left':
            new_extended_display_text = transition_text
            new_extended_display_text.extend(new_display_text)

            if step < self.output_length:
                temp_text = current_display_text[:self.output_length - (step + 1)]
                temp_text.extend(new_extended_display_text[:step + 1])
            else:
                temp_text = new_extended_display_text[step - self.output_length + 1:step + 1]

            return temp_text

        raise AssertionError(TRANSITION_DIRECTION_UNKNOWN_ERROR)


class UncoverTransition(TransitionBase):

    """Segment display uncover transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool,
                 config: dict) -> None:
        """Class initializer."""
        self.direction = 'right'
        self.text = None
        self.text_color = None
        super().__init__(output_length, collapse_dots, collapse_commas, use_dots_for_commas, config)

        if self.text is None:
            self.text = ''

    def get_step_count(self):
        """Return the total number of steps required for the transition."""
        return self.output_length + len(self.text)

    # pylint: disable=too-many-arguments
    def get_transition_step(self, step: int, current_text: str, new_text: str,
                            current_colors: Optional[List[RGBColor]] = None,
                            new_colors: Optional[List[RGBColor]] = None) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError(STEP_OUT_OF_RANGE_ERROR)

        current_display_text = SegmentDisplayText.from_str(current_text, self.output_length, self.collapse_dots,
                                                           self.collapse_commas, self.use_dots_for_commas, 
                                                           current_colors)
        new_display_text = SegmentDisplayText.from_str(new_text, self.output_length, self.collapse_dots,
                                                       self.collapse_commas, self.use_dots_for_commas, new_colors)

        if self.text:
            if new_colors and not self.text_color:
                text_color = [new_colors[0]]
            else:
                text_color = self.text_color
            transition_text = SegmentDisplayText.from_str(self.text, len(self.text), self.collapse_dots,
                                                          self.collapse_commas, self.use_dots_for_commas, text_color)
        else:
            transition_text = UncoloredSegmentDisplayText([], self.collapse_dots, self.collapse_commas, 
                                                          self.use_dots_for_commas)

        if self.direction == 'right':
            current_extended_display_text = transition_text
            current_extended_display_text.extend(current_display_text)

            if step < len(self.text):
                temp_text = current_extended_display_text[
                    len(self.text) - step - 1:len(self.text) - step - 1 + self.output_length]
            else:
                temp_text = new_display_text[:step - len(self.text) + 1]
                temp_text.extend(current_extended_display_text[:self.output_length - len(temp_text)])

            return temp_text

        if self.direction == 'left':
            current_extended_display_text = current_display_text
            current_extended_display_text.extend(transition_text)

            if step < len(self.text):
                temp_text = current_extended_display_text[step + 1:step + 1 + self.output_length]
            else:
                temp_text = current_display_text[step + 1:]
                temp_text.extend(new_display_text[-(self.output_length - len(temp_text)):])
            return temp_text

        raise AssertionError(TRANSITION_DIRECTION_UNKNOWN_ERROR)


class WipeTransition(TransitionBase):

    """Segment display wipe transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool,
                 config: dict) -> None:
        """Class initializer."""
        self.direction = 'right'
        self.text = None
        self.text_color = None
        super().__init__(output_length, collapse_dots, collapse_commas, use_dots_for_commas, config)

        if self.text is None:
            self.text = ''

    def get_step_count(self):
        """Return the total number of steps required for the transition."""
        return self.output_length + len(self.text)

    # pylint: disable=too-many-arguments,too-many-branches,too-many-return-statements
    def get_transition_step(self, step: int, current_text: str, new_text: str,
                            current_colors: Optional[List[RGBColor]] = None,
                            new_colors: Optional[List[RGBColor]] = None) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError(STEP_OUT_OF_RANGE_ERROR)

        current_display_text = SegmentDisplayText.from_str(current_text, self.output_length, self.collapse_dots,
                                                           self.collapse_commas, self.use_dots_for_commas,
                                                           current_colors)
        new_display_text = SegmentDisplayText.from_str(new_text, self.output_length, self.collapse_dots,
                                                       self.collapse_commas, self.use_dots_for_commas, new_colors)

        if self.text:
            if new_colors and not self.text_color:
                text_color = [new_colors[0]]
            else:
                text_color = self.text_color
            transition_text = SegmentDisplayText.from_str(self.text, len(self.text), self.collapse_dots,
                                                          self.collapse_commas, self.use_dots_for_commas, text_color)
        else:
            transition_text = UncoloredSegmentDisplayText([], self.collapse_dots, self.collapse_commas, 
                                                          self.use_dots_for_commas)

        if self.direction == 'right':
            if step < len(self.text):
                temp_text = transition_text[-(step + 1):]
                temp_text.extend(current_display_text[step + 1:])
            elif step < self.output_length:
                temp_text = new_display_text[:step - len(self.text) + 1]
                temp_text.extend(transition_text)
                temp_text.extend(current_display_text[len(temp_text):])
            else:
                temp_text = new_display_text[:step - len(self.text) + 1]
                temp_text.extend(transition_text[:self.output_length - len(temp_text)])
            return temp_text

        if self.direction == 'left':
            if step < len(self.text):
                temp_text = current_display_text[:self.output_length - (step + 1)]
                temp_text.extend(transition_text[:step + 1])
            elif step < self.output_length:
                temp_text = current_display_text[:self.output_length - (step + 1)]
                temp_text.extend(transition_text)
                temp_text.extend(new_display_text[len(temp_text):])
            elif step < self.output_length + len(self.text) - 1:
                temp_text = transition_text[step - (self.output_length + len(self.text)) + 1:]
                temp_text.extend(new_display_text[-(self.output_length - len(temp_text)):])
            else:
                temp_text = new_display_text
            return temp_text

        raise AssertionError(TRANSITION_DIRECTION_UNKNOWN_ERROR)


class SplitTransition(TransitionBase):

    """Segment display split transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, use_dots_for_commas: bool,
                 config: dict) -> None:
        """Class initializer."""
        self.direction = 'out'
        self.mode = 'push'
        super().__init__(output_length, collapse_dots, collapse_commas, use_dots_for_commas, config)

    def get_step_count(self):
        """Return the total number of steps required for the transition."""
        return int((self.output_length + 1) / 2)

    # pylint: disable=too-many-arguments,too-many-branches,too-many-return-statements
    def get_transition_step(self, step: int, current_text: str, new_text: str,
                            current_colors: Optional[List[RGBColor]] = None,
                            new_colors: Optional[List[RGBColor]] = None) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError(STEP_OUT_OF_RANGE_ERROR)

        current_display_text = SegmentDisplayText.from_str(current_text, self.output_length, self.collapse_dots,
                                                           self.collapse_commas, self.use_dots_for_commas,
                                                           current_colors)
        new_display_text = SegmentDisplayText.from_str(new_text, self.output_length, self.collapse_dots,
                                                       self.collapse_commas, self.use_dots_for_commas, new_colors)

        if self.mode == 'push':
            if self.direction == 'out':
                if step == self.get_step_count() - 1:
                    return new_display_text

                characters = int(self.output_length / 2)
                split_point = characters
                if characters * 2 == self.output_length:
                    characters -= 1
                else:
                    split_point += 1

                characters -= step
                temp_text = current_display_text[split_point - characters:split_point]
                temp_text.extend(new_display_text[characters:characters + (self.output_length - 2 * characters)])
                temp_text.extend(current_display_text[split_point:split_point + characters])
                return temp_text

            if self.direction == 'in':
                if step == self.get_step_count() - 1:
                    return new_display_text

                split_point = int(self.output_length / 2)
                characters = 1
                if split_point * 2 < self.output_length:
                    split_point += 1

                characters += step
                temp_text = new_display_text[split_point - characters:split_point]
                temp_text.extend(current_display_text[characters:characters + (self.output_length - 2 * characters)])
                temp_text.extend(new_display_text[split_point:split_point + characters])
                return temp_text

            raise AssertionError(TRANSITION_DIRECTION_UNKNOWN_ERROR)

        if self.mode == 'wipe':
            if self.direction == 'out':
                if step == self.get_step_count() - 1:
                    return new_display_text

                characters = int(self.output_length / 2)
                if characters * 2 == self.output_length:
                    characters -= 1

                characters -= step
                temp_text = current_display_text[:characters]
                temp_text.extend(new_display_text[characters:characters + (self.output_length - 2 * characters)])
                temp_text.extend(current_display_text[-characters:])
                return temp_text

            if self.direction == 'in':
                if step == self.get_step_count() - 1:
                    return new_display_text

                temp_text = new_display_text[:step + 1]
                temp_text.extend(current_display_text[step + 1:step + 1 + (self.output_length - 2 * len(temp_text))])
                temp_text.extend(new_display_text[-(step + 1):])
                return temp_text

            raise AssertionError(TRANSITION_DIRECTION_UNKNOWN_ERROR)

        raise AssertionError("Transition uses an unknown mode value")
