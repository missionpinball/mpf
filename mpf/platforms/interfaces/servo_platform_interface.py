"""Platform interface for servos."""
from typing import List

import abc


class ServoPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for servos in hardware platforms.

    ServoPlatformInterface is an abstract base class that should be overridden for all
    servo interface classes on supported platforms.  This class ensures the proper required
    methods are implemented to support servo operations in MPF.
    """

    __slots__ = []  # type: List[str]

    @abc.abstractmethod
    def go_to_position(self, position):
        """Move servo to a certain position."""
        raise NotImplementedError

    def set_speed_limit(self, speed_limit):
        """Set speed limit."""

    def set_acceleration_limit(self, acceleration_limit):
        """Set acceleration limit."""

    def stop(self):
        """Stop this servo.

        This should disable the output or home the servo.
        """
