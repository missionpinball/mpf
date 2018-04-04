"""I2C platform which uses the smbus interface on linux via the smbus2 python extension."""
import asyncio
from typing import Dict, Tuple

from mpf.core.utility_functions import Util

from mpf.core.platform import I2cPlatform

extension_loaded = True
# pylint: disable-msg=ungrouped-imports
try:
    from smbus2_asyncio import SMBus2Asyncio
except ImportError:     # pragma: no cover
    SMBus2Asyncio = None


class Smbus2(I2cPlatform):

    """I2C platform which uses the smbus interface on linux via the smbus2 python extension."""

    def __init__(self, machine):
        """Initialise smbus2 platform."""
        super().__init__(machine)
        self._i2c_handles = {}  # type: Dict[int, SMBus2Asyncio]

    @asyncio.coroutine
    def initialize(self):
        """Check if smbus2 extension has been imported."""
        if not SMBus2Asyncio:
            raise AssertionError("smbus2 python extension missing. Please run: pip3 install smbus2_asyncio")

    @staticmethod
    def _get_i2c_bus_address(address) -> Tuple[int, int]:
        """Split and return bus + address."""
        if isinstance(address, int):
            return 0, address
        bus, address = address.split("-")
        return bus, int(address)

    def _get_i2c_bus(self, bus) -> SMBus2Asyncio:
        """Get or open handle for i2c bus."""
        if bus in self._i2c_handles:
            return self._i2c_handles[bus]
        handle = SMBus2Asyncio(bus, loop=self.machine.clock.loop)
        handle.open_sync()
        self._i2c_handles[bus] = handle
        return handle

    @asyncio.coroutine
    def i2c_read8(self, address, register):
        """Read a byte from I2C."""
        bus, address = self._get_i2c_bus_address(address)
        smbus = self._get_i2c_bus(bus)
        return (yield from smbus.read_byte_data(address, int(register)))

    def i2c_write8(self, address, register, value):
        """Write a byte to I2C."""
        bus, address = self._get_i2c_bus_address(address)
        smbus = self._get_i2c_bus(bus)
        Util.ensure_future(smbus.write_byte_data(address, int(register), int(value)), loop=self.machine.clock.loop)
        # this does not return

    @asyncio.coroutine
    def i2c_read_block(self, address, register, count):
        """Read a block from I2C."""
        bus, address = self._get_i2c_bus_address(address)
        smbus = self._get_i2c_bus(bus)
        return (yield from smbus.read_i2c_block_data(address, int(register), int(count)))
