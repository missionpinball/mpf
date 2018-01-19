"""I2C platform which uses the smbus interface on linux via the smbus2 python extension."""
import asyncio
from typing import Any

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
        self.smbus = None   # type: SMBus
        self.config = None  # type: Any

    @asyncio.coroutine
    def initialize(self):
        """Check if smbus2 extension has been imported."""
        if not SMBus:
            raise AssertionError("smbus2 python extension missing. Please run: pip3 install smbus2")

        self.config = self.machine.config_validator.validate_config("smbus2", self.machine.config['smbus2'])

        self.smbus = SMBus(self.config['bus'])  # type: SMBus

    @asyncio.coroutine
    def i2c_read8(self, address, register):
        """Read a byte from I2C."""
        return self.smbus.read_byte_data(int(address), int(register))

    def i2c_write8(self, address, register, value):
        """Write a byte to I2C."""
        return self.smbus.write_byte_data(int(address), int(register), int(value))

    @asyncio.coroutine
    def i2c_read_block(self, address, register, count):
        """Read a block from I2C."""
        return self.smbus.read_i2c_block_data(int(address), int(register), int(count))
