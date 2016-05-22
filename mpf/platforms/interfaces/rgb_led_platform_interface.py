"""Interface for RGB hardware devices/LEDs."""
import abc


class RGBLEDPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for LEDs in hardware platforms.

    LEDPlatformInterface is an abstract base class that should be overridden for all LED
    interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support LED operations in MPF.
    """

    @abc.abstractmethod
    def color(self, color):
        """Set the LED to the specified color.

        Args:
            color: a list of int colors. one for each channel.

        Returns:
            None
        """
        raise NotImplementedError('color method must be defined to use this base class')
