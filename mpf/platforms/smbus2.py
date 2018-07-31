"""I2C platform which uses the smbus interface on linux via the smbus2 python extension."""
import asyncio
from typing import Dict, Tuple, Generator

import logging

from mpf.platforms.interfaces.i2c_platform_interface import I2cPlatformInterface

from mpf.core.utility_functions import Util

from mpf.core.platform import I2cPlatform

extension_loaded = True
# pylint: disable-msg=ungrouped-imports
try:
    from smbus2_asyncio import SMBus2Asyncio
except ImportError:     # pragma: no cover
    SMBus2Asyncio = None


class Smbus2I2cDevice(I2cPlatformInterface):

    """A i2c device on smbus2."""

    __slots__ = ["loop", "platform", "busses", "address", "smbus"]

    def __init__(self, number: str, platform, busses) -> None:
        """Initialise smbus2 device."""
        super().__init__(number)
        self.loop = platform.machine.clock.loop
        self.platform = platform
        self.busses = busses
        bus, self.address = self._get_i2c_bus_address(number)
        self.smbus = self._get_i2c_bus(bus)

    @asyncio.coroutine
    def open(self):
        """Open device (if not already open)."""
        while not self.smbus.smbus:
            try:
                yield from self.smbus.open()
            except FileNotFoundError:
                if not self.platform.machine.options["production"]:
                    raise
                else:
                    # if we are in production mode retry
                    yield from asyncio.sleep(.1, loop=self.platform.machine.clock.loop)
                    self.platform.log.debug("Connection to %s failed. Will retry.", self.number)
            else:
                break

    @staticmethod
    def _get_i2c_bus_address(address) -> Tuple[int, int]:
        """Split and return bus + address."""
        if isinstance(address, int):
            return 0, address
        bus, address = address.split("-", 1)
        return bus, int(address)

    def _get_i2c_bus(self, bus) -> SMBus2Asyncio:
        """Get or open handle for i2c bus."""
        if bus in self.busses:
            return self.busses[bus]
        handle = SMBus2Asyncio(bus, loop=self.loop)
        self.busses[bus] = handle
        return handle

    @asyncio.coroutine
    def i2c_read8(self, register):
        """Read a byte from I2C."""
        return (yield from self.smbus.read_byte_data(self.address, int(register)))

    def i2c_write8(self, register, value):
        """Write a byte to I2C."""
        Util.ensure_future(self.smbus.write_byte_data(self.address, int(register), int(value)), loop=self.loop)
        # this does not return

    @asyncio.coroutine
    def i2c_read_block(self, register, count):
        """Read a block from I2C."""
        return (yield from self.smbus.read_i2c_block_data(self.address, int(register), int(count)))


class Smbus2(I2cPlatform):

    """I2C platform which uses the smbus interface on linux via the smbus2 python extension."""

    __slots__ = ["_i2c_busses"]

    def __init__(self, machine):
        """Initialise Smbus2 platform."""
        super().__init__(machine)
        self._i2c_busses = {}
        self.log = logging.getLogger('Smbus2')

    @asyncio.coroutine
    def initialize(self):
        """Check if smbus2 extension has been imported."""
        if not SMBus2Asyncio:
            raise AssertionError("smbus2 python extension missing. Please run: pip3 install smbus2_asyncio")

    @asyncio.coroutine
    def configure_i2c(self, number: str) -> Generator[int, None, Smbus2I2cDevice]:
        """Configure device on smbus2."""
        device = Smbus2I2cDevice(number, self, self._i2c_busses)
        yield from device.open()
        return device
