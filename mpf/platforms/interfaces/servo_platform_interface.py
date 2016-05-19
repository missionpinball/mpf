import abc


class ServoPlatformInterface(metaclass=abc.ABCMeta):
    """
    ServoPlatformInterface is an abstract base class that should be overridden for all
    servo interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support servo operations in MPF.
    """

    @abc.abstractmethod
    def go_to_position(self, position):
        raise NotImplementedError()
