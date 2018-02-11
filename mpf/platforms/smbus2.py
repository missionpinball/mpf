"""I2C platform which uses the smbus interface on linux via the smbus2 python extension."""
import asyncio
from typing import Dict, Tuple

from mpf.core.platform import I2cPlatform

extension_loaded = True
# pylint: disable-msg=ungrouped-imports
try:
    from smbus2 import SMBus
except ImportError:     # pragma: no cover
    SMBus = None


class Smbus2(I2cPlatform):

    """I2C platform which uses the smbus interface on linux via the smbus2 python extension."""

    def __init__(self, machine):
        """Initialise smbus2 platform."""
        super().__init__(machine)
        self._i2c_handles = {}  # type: Dict[int, SMBus]

    @asyncio.coroutine
    def initialize(self):
        """Check if smbus2 extension has been imported."""
        if not SMBus:
            raise AssertionError("smbus2 python extension missing. Please run: pip3 install smbus2")

    @staticmethod
    def _get_i2c_bus_address(address) -> Tuple[int, int]:
        """Split and return bus + address."""
        if isinstance(address, int):
            return 0, address
        bus, address = address.split("-")
        return bus, int(address)

    def _get_i2c_bus(self, bus) -> SMBus:
        """Get or open handle for i2c bus."""
        if bus in self._i2c_handles:
            return self._i2c_handles[bus]
        handle = SMBus(bus)
        self._i2c_handles[bus] = handle
        return handle

    @asyncio.coroutine
    def i2c_read8(self, address, register):
        """Read a byte from I2C."""
        bus, address = self._get_i2c_bus_address(address)
        smbus = self._get_i2c_bus(bus)
        return smbus.read_byte_data(address, int(register))

    def i2c_write8(self, address, register, value):
        """Write a byte to I2C."""
        bus, address = self._get_i2c_bus_address(address)
        smbus = self._get_i2c_bus(bus)
        return smbus.write_byte_data(address, int(register), int(value))

    @asyncio.coroutine
    def i2c_read_block(self, address, register, count):
        """Read a block from I2C."""
        bus, address = self._get_i2c_bus_address(address)
        smbus = self._get_i2c_bus(bus)
        return smbus.read_i2c_block_data(address, int(register), int(count))
