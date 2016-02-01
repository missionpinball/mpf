import abc


class GIPlatformInterface(metaclass=abc.ABCMeta):
    """
    GIPlatformInterface is an abstract base class that should be overridden for all
    GI interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support GI operations in MPF.
    """

    @abc.abstractmethod
    def on(self, brightness):
        """
        Sets the GI to the specified brightness level.
        Args:
            brightness: Integer (0 to 255) that sets the brightness level of the GI

        Returns:
            None
        """
        raise NotImplementedError('on method must be defined to use this base class')

    @abc.abstractmethod
    def off(self):
        """
        Turns off the GI instantly.
        Returns:
            None
        """
        raise NotImplementedError('off method must be defined to use this base class')
