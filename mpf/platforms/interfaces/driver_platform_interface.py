"""Interface for drivers."""
import abc


class DriverPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for drivers in hardware platforms.

    DriverPlatformInterface is an abstract base class that should be overridden for all
    driver interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support driver operations in MPF.
    """

    def __init__(self, config, number):
        """Initialise driver."""
        self.number = number
        self.config = config

    @abc.abstractmethod
    def disable(self, coil):
        """Disable the driver."""
        raise NotImplementedError('disable method must be defined to use this base class')

    @abc.abstractmethod
    def enable(self, coil):
        """Enable this driver, which means it's held "on" indefinitely until it's explicitly disabled."""
        raise NotImplementedError('enable method must be defined to use this base class')

    @abc.abstractmethod
    def get_board_name(self):
        """Return the name of the board of this driver."""
        raise NotImplementedError('implement')

    @abc.abstractmethod
    def pulse(self, coil, milliseconds):
        """Pulse a driver.

        Pulse this driver for a pre-determined amount of time, after which
        this driver is turned off automatically. Note that on most platforms,
        pulse times are a max of 255ms. (Beyond that MPF will send separate
        enable() and disable() commands.

        Args:
            milliseconds: The number of ms to pulse this driver for. You should
                raise a ValueError if the value is out of range for your
                platform.

        Returns:
            A integer of the actual time this driver is going to be pulsed for.
            MPF uses this for timing in certain situations to make sure too
            many drivers aren't activated at once.

        """
        raise NotImplementedError('pulse method must be defined to use this base class')
