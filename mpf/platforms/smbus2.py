"""I2C platform which uses the smbus interface on linux via the smbus2 python extension."""
import asyncio
from typing import Dict, Tuple, Generator

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

    def __init__(self, number: str, loop, busses) -> None:
        """Initialise smbus2 device."""
        super().__init__(number)
        self.loop = loop
        self.busses = busses
        bus, self.address = self._get_i2c_bus_address(number)
        self.smbus = self._get_i2c_bus(bus)

    @asyncio.coroutine
    def open(self):
        """Open device (if not already open)."""
        if not self.smbus.smbus:
            yield from self.smbus.open()

    @staticmethod
    def _get_i2c_bus_address(address) -> Tuple[int, int]:
        """Split and return bus + address."""
        if isinstance(address, int):
            return 0, address
        bus, address = address.split("-")
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

    def __init__(self, machine):
        """Initialise Smbus2 platform."""
        super().__init__(machine)
        self._i2c_busses = {}

    @asyncio.coroutine
    def initialize(self):
        """Check if smbus2 extension has been imported."""
        if not SMBus2Asyncio:
            raise AssertionError("smbus2 python extension missing. Please run: pip3 install smbus2_asyncio")

    @asyncio.coroutine
    def configure_i2c(self, number: str) -> Generator[int, None, Smbus2I2cDevice]:
        """Configure device on smbus2."""
        device = Smbus2I2cDevice(number, self.machine.clock.loop, self._i2c_busses)
        yield from device.open()
        return device
