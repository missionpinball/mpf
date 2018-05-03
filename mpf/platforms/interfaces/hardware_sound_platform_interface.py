"""Interface for a hardware sound platform."""
import abc


class HardwareSoundPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a hardware sound platform."""

    @abc.abstractmethod
    def play_sound(self, number: int):
        """Play a sound."""
        raise NotImplementedError

    @abc.abstractmethod
    def play_sound_file(self, file: str, platform_options: dict):
        """Play a sound file."""
        raise NotImplementedError

    @abc.abstractmethod
    def text_to_speech(self, text: str, platform_options: dict):
        """Text to speech output."""
        raise NotImplementedError

    @abc.abstractmethod
    def set_volume(self, volume: float):
        """Set volume."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop_all_sounds(self):
        """Play a sound."""
        raise NotImplementedError
