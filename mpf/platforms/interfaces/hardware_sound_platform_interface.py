"""Interface for a hardware sound platform."""
from typing import List

import abc


class HardwareSoundPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a hardware sound platform."""

    __slots__ = []  # type: List[str]

    @abc.abstractmethod
    def play_sound(self, number: int, track: int = 1):
        """Play a sound."""
        raise NotImplementedError

    @abc.abstractmethod
    def play_sound_file(self, file: str, platform_options: dict, track: int = 1):
        """Play a sound file."""
        raise NotImplementedError

    @abc.abstractmethod
    def text_to_speech(self, text: str, platform_options: dict, track: int = 1):
        """Text to speech output."""
        raise NotImplementedError

    @abc.abstractmethod
    def set_volume(self, volume: float, track: int = 1):
        """Set volume."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop_all_sounds(self, track: int = 1):
        """Play a sound."""
        raise NotImplementedError
