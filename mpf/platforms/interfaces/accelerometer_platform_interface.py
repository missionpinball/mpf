"""Interface for an accelerometer device."""
from typing import List

import abc


class AccelerometerPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for accelerometer devices in platforms.

    Currently no public methods.
    """

    __slots__ = []  # type: List[str]
