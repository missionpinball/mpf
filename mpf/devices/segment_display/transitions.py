"""Text transitions used for segment displays."""
import abc

from mpf.core.placeholder_manager import TextTemplate
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText


class TransitionBase(metaclass=abc.ABCMeta):

    """Base class for text transitions in segment displays."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        """Initialize the transition"""
        self.output_length = output_length
        self.config = config
        self.collapse_dots = collapse_dots
        self.collapse_commas = collapse_commas

        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @abc.abstractmethod
    def get_step_count(self):
        """Return the total number of steps required for the transition"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_transition_step(self, step: int, current_text: str, new_text: str) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        raise NotImplementedError


class TransitionRunner:

    """Class to run/execute transitions using an iterator."""

    def __init__(self, machine, transition: TransitionBase, current_text: str, new_text: str):
        """Class initializer."""
        self.machine = machine
        self.transition = transition
        self.step = 0
        self.current_placeholder = TextTemplate(self.machine, current_text)
        self.new_placeholder = TextTemplate(self.machine, new_text)

    def __iter__(self):
        """Returns an iterator"""
        return self

    def __next__(self):
        """Evaluate and return the next transition step."""
        if self.step >= self.transition.get_step_count():
            raise StopIteration

        transition_step = self.transition.get_transition_step(self.step,
                                                              self.current_placeholder.evaluate({}),
                                                              self.new_placeholder.evaluate({}))
        self.step += 1
        return transition_step


class NoTransition(TransitionBase):

    """Segment display no transition effect."""

    def get_step_count(self):
        """Return the total number of steps required for the transition"""
        return 1

    def get_transition_step(self, step: int, current_text: str,
                            new_text: str) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError("Step is out of range")

        return SegmentDisplayText(new_text, self.output_length, self.collapse_dots, self.collapse_commas)


class PushTransition(TransitionBase):

    """Segment display push transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(output_length, collapse_dots, collapse_commas, config)

    def get_step_count(self):
        """Return the total number of steps required for the transition"""
        if self.direction in ['split_out', 'split_in']:
            return int((self.output_length + 1) / 2)

        return self.output_length

    def get_transition_step(self, step: int, current_text: str, new_text: str) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError("Step is out of range")

        current_display_text = SegmentDisplayText(current_text, self.output_length, self.collapse_dots,
                                                  self.collapse_commas)
        new_display_text = SegmentDisplayText(new_text, self.output_length, self.collapse_dots, self.collapse_commas)

        if self.direction == 'right':
            temp_list = new_display_text
            temp_list.extend(current_display_text)
            return temp_list[self.output_length - (step + 1):2 * self.output_length - (step + 1)]

        if self.direction == 'left':
            temp_list = current_display_text
            temp_list.extend(new_display_text)
            return temp_list[step + 1:step + 1 + self.output_length]

        if self.direction == 'split_out':
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

        if self.direction == 'split_in':
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

        raise AssertionError("Transition uses an unknown direction value")


class CoverTransition(TransitionBase):

    """Segment display cover transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(output_length, collapse_dots, collapse_commas, config)

    def get_step_count(self):
        """Return the total number of steps required for the transition"""
        return self.output_length

    def get_transition_step(self, step: int, current_text: str, new_text: str) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError("Step is out of range")

        current_display_text = SegmentDisplayText(current_text, self.output_length, self.collapse_dots,
                                                  self.collapse_commas)
        new_display_text = SegmentDisplayText(new_text, self.output_length, self.collapse_dots, self.collapse_commas)

        if self.direction == 'right':
            temp_text = new_display_text[-(step + 1):]
            temp_text.extend(current_display_text[step + 1:])
            return temp_text

        if self.direction == 'left':
            temp_text = current_display_text[:self.output_length - (step + 1)]
            temp_text.extend(new_display_text[:step + 1])
            return temp_text

        raise AssertionError("Transition uses an unknown direction value")


class UncoverTransition(TransitionBase):

    """Segment display uncover transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(output_length, collapse_dots, collapse_commas, config)

    def get_step_count(self):
        """Return the total number of steps required for the transition"""
        return self.output_length

    def get_transition_step(self, step: int, current_text: str, new_text: str) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError("Step is out of range")

        current_display_text = SegmentDisplayText(current_text, self.output_length, self.collapse_dots,
                                                  self.collapse_commas)
        new_display_text = SegmentDisplayText(new_text, self.output_length, self.collapse_dots, self.collapse_commas)

        if self.direction == 'right':
            temp_text = new_display_text[:step + 1]
            temp_text.extend(current_display_text[:self.output_length - (step + 1)])
            return temp_text

        if self.direction == 'left':
            temp_text = current_display_text[step + 1:]
            temp_text.extend(new_display_text[-(step + 1):])
            return temp_text

        raise AssertionError("Transition uses an unknown direction value")


class WipeTransition(TransitionBase):

    """Segment display wipe transition effect."""

    def __init__(self, output_length: int, collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(output_length, collapse_dots, collapse_commas, config)

    def get_step_count(self):
        """Return the total number of steps required for the transition"""
        if self.direction == 'split':
            return int((self.output_length + 1) / 2)

        return self.output_length

    def get_transition_step(self, step: int, current_text: str, new_text: str) -> SegmentDisplayText:
        """Calculate all the steps in the transition."""
        if step < 0 or step >= self.get_step_count():
            raise AssertionError("Step is out of range")

        current_display_text = SegmentDisplayText(current_text, self.output_length, self.collapse_dots,
                                                  self.collapse_commas)
        new_display_text = SegmentDisplayText(new_text, self.output_length, self.collapse_dots, self.collapse_commas)

        if self.direction == 'right':
            temp_text = new_display_text[:step + 1]
            temp_text.extend(current_display_text[step + 1:])
            return temp_text

        if self.direction == 'left':
            temp_text = current_display_text[:self.output_length - (step + 1)]
            temp_text.extend(new_display_text[-(step + 1):])
            return temp_text

        if self.direction == 'split':
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

        raise AssertionError("Transition uses an unknown direction value")
