"""Platform interface for servos."""
import abc


class ServoPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for servos in hardware platforms.

    ServoPlatformInterface is an abstract base class that should be overridden for all
    servo interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support servo operations in MPF.
    """

    @abc.abstractmethod
    def go_to_position(self, position):
        """Move servo to a certain position."""
        raise NotImplementedError
