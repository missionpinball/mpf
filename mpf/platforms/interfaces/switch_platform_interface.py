"""Interface for switches."""
import abc


class SwitchPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for switches in hardware platforms.

    SwitchPlatformInterface is an abstract base class that should be overridden for all
    switches interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support switch operations in MPF.
    """

    def __init__(self, config, number):
        """Initialise default attributes for switches."""
        self.config = config
        self.number = number
