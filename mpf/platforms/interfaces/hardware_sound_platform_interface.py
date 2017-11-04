"""Interface for a hardware sound platform."""
import abc


class HardwareSoundPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a light in hardware platforms."""

    @abc.abstractmethod
    def play_sound(self, number: int):
        """Play a sound."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop_all_sounds(self):
        """Play a sound."""
        raise NotImplementedError
