"""Text transitions used for segment displays."""
import abc
from typing import List

from mpf.devices.segment_display.segment_display_text import SegmentDisplayText


class TransitionBase(metaclass=abc.ABCMeta):

    """Base class for text transitions in segment displays."""

    # String of the config section name
    config_section = None   # type: str

    def __init__(self, current_text: str, new_text: str, output_length: int, collapse_dots: bool,
                 collapse_commas: bool, config: dict) -> None:
        """Initialize the transition"""
        self.current_text = SegmentDisplayText(current_text, output_length, collapse_dots, collapse_commas)
        self.new_text = SegmentDisplayText(new_text, output_length, collapse_dots, collapse_commas)
        self.output_length = output_length
        self.config = config
        self.transition_steps = []  # type: List[SegmentDisplayText]

        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.transition_steps = self.calculate_transition_steps(self.current_text, self.new_text)

    @abc.abstractmethod
    def calculate_transition_steps(self, current_text: SegmentDisplayText,
                                   new_text: SegmentDisplayText) -> List[SegmentDisplayText]:
        """Calculate all the steps in the transition."""
        raise NotImplementedError


class NoTransition(TransitionBase):

    """Segment display no transition effect."""

    config_section = 'text_transition_none'

    def __init__(self, current_text: str, new_text: str, output_length: int,
                 collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        super().__init__(current_text, new_text, output_length, collapse_dots, collapse_commas, config)

    def calculate_transition_steps(self, current_text: SegmentDisplayText,
                                   new_text: SegmentDisplayText) -> List[SegmentDisplayText]:
        """Calculate all the steps in the transition."""
        return [new_text]


class PushTransition(TransitionBase):

    """Segment display push transition effect."""

    config_section = 'text_transition_push'

    def __init__(self, current_text: str, new_text: str, output_length: int,
                 collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(current_text, new_text, output_length, collapse_dots, collapse_commas, config)

    def calculate_transition_steps(self, current_text: SegmentDisplayText,
                                   new_text: SegmentDisplayText) -> List[SegmentDisplayText]:
        """Calculate all the steps in the transition."""
        display_length = len(current_text)
        transition_steps = []

        if self.direction == 'right':
            temp_list = new_text
            temp_list.extend(current_text)

            for index in range(1, display_length + 1):
                transition_steps.append(temp_list[display_length - index:2 * display_length - index])

        elif self.direction == 'left':
            temp_list = current_text
            temp_list.extend(new_text)

            for index in range(1, display_length + 1):
                transition_steps.append(temp_list[index:index + display_length])

        elif self.direction == 'split_out':
            characters = int(display_length / 2)
            split_point = characters
            if characters * 2 == display_length:
                characters -= 1
            else:
                split_point += 1

            while characters > 0:
                temp_text = current_text[split_point - characters:split_point]
                temp_text.extend(new_text[characters:characters + (display_length - 2 * characters)])
                temp_text.extend(current_text[split_point:split_point + characters])
                transition_steps.append(temp_text)
                characters -= 1

            transition_steps.append(new_text)

        elif self.direction == 'split_in':
            split_point = int(display_length / 2)
            characters = 1
            if split_point * 2 < display_length:
                split_point += 1

            while characters <= split_point:
                temp_text = new_text[split_point - characters:split_point]
                temp_text.extend(current_text[characters:characters + (display_length - 2 * characters)])
                temp_text.extend(new_text[split_point:split_point + characters])
                transition_steps.append(temp_text)
                characters += 1

        return transition_steps


class CoverTransition(TransitionBase):

    """Segment display cover transition effect."""

    config_section = 'text_transition_cover'

    def __init__(self, current_text: str, new_text: str, output_length: int,
                 collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(current_text, new_text, output_length, collapse_dots, collapse_commas, config)

    def calculate_transition_steps(self, current_text: SegmentDisplayText,
                                   new_text: SegmentDisplayText) -> List[SegmentDisplayText]:
        """Calculate all the steps in the transition."""
        display_length = len(current_text)
        transition_steps = []

        if self.direction == 'right':
            for index in range(display_length):
                temp_text = new_text[-(index + 1):]
                temp_text.extend(current_text[index + 1:])
                transition_steps.append(temp_text)

        elif self.direction == 'left':
            for index in range(1, display_length + 1):
                temp_text = current_text[:display_length - index]
                temp_text.extend(new_text[:index])
                transition_steps.append(temp_text)

        return transition_steps


class UncoverTransition(TransitionBase):

    """Segment display uncover transition effect."""

    config_section = 'text_transition_uncover'

    def __init__(self, current_text: str, new_text: str, output_length: int,
                 collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(current_text, new_text, output_length, collapse_dots, collapse_commas, config)

    def calculate_transition_steps(self, current_text: SegmentDisplayText,
                                   new_text: SegmentDisplayText) -> List[SegmentDisplayText]:
        """Calculate all the steps in the transition."""
        display_length = len(current_text)
        transition_steps = []

        if self.direction == 'right':
            for index in range(1, display_length + 1):
                temp_text = new_text[:index]
                temp_text.extend(current_text[:display_length - index])
                transition_steps.append(temp_text)

        elif self.direction == 'left':
            for index in range(1, display_length + 1):
                temp_text = current_text[index:]
                temp_text.extend(new_text[-index:])
                transition_steps.append(temp_text)

        return transition_steps


class WipeTransition(TransitionBase):

    """Segment display wipe transition effect."""

    config_section = 'text_transition_wipe'

    def __init__(self, current_text: str, new_text: str, output_length: int,
                 collapse_dots: bool, collapse_commas: bool, config: dict) -> None:
        self.direction = 'right'
        super().__init__(current_text, new_text, output_length, collapse_dots, collapse_commas, config)

    def calculate_transition_steps(self, current_text: SegmentDisplayText,
                                   new_text: SegmentDisplayText) -> List[SegmentDisplayText]:
        """Calculate all the steps in the transition."""
        display_length = len(current_text)
        transition_steps = []

        if self.direction == 'right':
            for index in range(1, display_length + 1):
                temp_text = new_text[:index]
                temp_text.extend(current_text[index:])
                transition_steps.append(temp_text)

        elif self.direction == 'left':
            for index in range(1, display_length + 1):
                temp_text = current_text[:display_length - index]
                temp_text.extend(new_text[-index:])
                transition_steps.append(temp_text)

        elif self.direction == 'split':
            characters = int(display_length / 2)
            if characters * 2 == display_length:
                characters -= 1

            while characters > 0:
                temp_text = current_text[:characters]
                temp_text.extend(new_text[characters:characters + (display_length - 2 * characters)])
                temp_text.extend(current_text[-characters:])
                transition_steps.append(temp_text)
                characters -= 1

            transition_steps.append(new_text)

        return transition_steps
