"""Support for i2c devices on a bus."""
import abc
import asyncio
from typing import Any


class I2cPlatformInterface(metaclass=abc.ABCMeta):

    """Interface for a i2c device on a bus in hardware platforms."""

    __slots__ = ["number"]

    def __init__(self, number: Any) -> None:
        """Remember the number."""
        self.number = number

    @abc.abstractmethod
    def i2c_write8(self, register, value):
        """Write an 8-bit value to a specific register via I2C.

        Args:
            register (int): Register
            value (int): Value to write
        """
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def i2c_read_block(self, register, count):
        """Read an len bytes from an register via I2C.

        Args:
            register (int): Register
            count (int): Bytes to read
        """
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def i2c_read8(self, register):
        """Read an 8-bit value from an register via I2C.

        Args:
            register (int): Register
        """
        raise NotImplementedError
