import abc


class RGBLEDPlatformInterface:
    """
    LEDPlatformInterface is an abstract base class that should be overridden for all LED
    interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support LED operations in MPF.
    """
    __metaclass__ = abc.ABCMeta

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

    @abc.abstractmethod
    def enable(self):
        """
        Enables (turns on) the RGB LED instantly.
        Returns:
            None
        """
        raise NotImplementedError('enable method must be defined to use this base class')

    @abc.abstractmethod
    def disable(self):
        """
        Disables (turns off) the RGB LED instantly.
        Returns:
            None
        """
        raise NotImplementedError('disable method must be defined to use this base class')

