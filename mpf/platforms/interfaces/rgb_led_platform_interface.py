import abc


class RGBLEDPlatformInterface(metaclass=abc.ABCMeta):
    """
    LEDPlatformInterface is an abstract base class that should be overridden for all LED
    interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support LED operations in MPF.
    """

    @abc.abstractmethod
    def color(self, color):
        """
        Sets the RGB LED to the specified color.
        Args:
            color: an RGBColor object

        Returns:
            None
        """
        raise NotImplementedError('color method must be defined to use this base class')
