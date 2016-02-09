import abc


class MatrixLightPlatformInterface(metaclass=abc.ABCMeta):
    """MatrixLightPlatformInterface is an abstract base class that should be
    overridden for all matrix light interface classes on supported
    platforms. This class ensures the proper required methods are
    implemented to support matrix light operations in MPF.
    """

    @abc.abstractmethod
    def on(self, brightness):
        """
        Sets the matrix light to the specified brightness level.
        Args:
            brightness: Integer (0 to 255) that sets the brightness level of the light

        Returns:
            None
        """
        raise NotImplementedError('on method must be defined to use this base class')

    @abc.abstractmethod
    def off(self):
        """
        Turns off the matrix light instantly.
        Returns:
            None
        """
        raise NotImplementedError('off method must be defined to use this base class')

