"""Interface for a light hardware devices."""
import abc


class LightPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a light in hardware platforms."""

    def get_max_fade_ms(self):
        """Return maximum fade_ms for this light."""
        return 0

    @abc.abstractmethod
    def set_brightness(self, brightness: float, fade_ms: int):
        """Set the light to the specified brightness.

        Args:
            brightness: float of the brightness
            fade_ms: ms to fade the light

        Returns:
            None
        """
        raise NotImplementedError('set_brightness method must be defined to use this base class')
