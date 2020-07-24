"""Interface for drivers."""
import abc
from collections import namedtuple
from typing import Any
from mpf.core.platform import DriverConfig


PulseSettings = namedtuple("PulseSettings", ["power", "duration"])
HoldSettings = namedtuple("HoldSettings", ["power"])


class DriverPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for drivers in hardware platforms.

    DriverPlatformInterface is an abstract base class that should be overridden for all
    driver interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support driver operations in MPF.
    """

    __slots__ = ["number", "config"]

    def __init__(self, config: DriverConfig, number: "Any") -> None:
        """Initialise driver."""
        self.number = number    # type: Any
        self.config = config    # type: DriverConfig

    @abc.abstractmethod
    def pulse(self, pulse_settings: PulseSettings):
        """Pulse a driver.

        Pulse this driver for a pre-determined amount of time, after which
        this driver is turned off automatically. Note that on most platforms,
        pulse times are a max of 255ms. (Beyond that MPF will send separate
        enable() and disable() commands.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable this driver, which means it's held "on" indefinitely until it's explicitly disabled."""
        raise NotImplementedError

    @abc.abstractmethod
    def disable(self):
        """Disable the driver."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_board_name(self):
        """Return the name of the board of this driver."""
        raise NotImplementedError

    def __repr__(self):
        """Return board + number."""
        return "<Driver {} {} (config: {})>".format(self.get_board_name(), self.number, self.config)
