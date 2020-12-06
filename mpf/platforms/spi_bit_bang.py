"""Bit bang SPI to read switches."""
from typing import List

import asyncio
import logging

from mpf.core.utility_functions import Util

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.core.platform import SwitchPlatform, SwitchConfig


class SpiBitBangSwitch(SwitchPlatformInterface):

    """Switch on SPI Bit Bang."""

    __slots__ = []  # type: List[str]

    def get_board_name(self):
        """Return board name."""
        return "SPI Big Bang"


class SpiBitBangPlatform(SwitchPlatform):

    """Platform which reads switch via SPI using bit banging."""

    __slots__ = ["_read_task", "config", "_switch_states"]

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Configure switch."""
        self._switch_states[number] = False
        return SpiBitBangSwitch(config, number)

    async def get_hw_switch_states(self):
        """Read initial hardware state.

        This will always be false for all inputs on those switches.
        """
        return self._switch_states

    def __init__(self, machine):
        """Initialise platform."""
        super().__init__(machine)
        self.log = logging.getLogger('SPI Bit Bang')
        self.log.debug("Configuring SPI Bit Bang.")
        self._read_task = None
        self.config = {}
        self._switch_states = {}

    def _enable_chip_select(self):
        self.config['cs_pin'].enable()

    def _disable_chip_select(self):
        self.config['cs_pin'].disable()

    async def initialize(self):
        """Register handler for late init."""
        self.machine.events.add_handler("init_phase_3", self._late_init)

    def _late_init(self, **kwargs):
        """Initialise this when other platforms are already loaded."""
        del kwargs
        self.config = self.machine.config_validator.validate_config("spi_bit_bang",
                                                                    self.machine.config.get('spi_bit_bang', {}))

        self._read_task = self.machine.clock.loop.create_task(self._run())
        self._read_task.add_done_callback(Util.raise_exceptions)

    async def read_spi(self, bits):
        """Read from SPI."""
        self.config['clock_pin'].disable()
        self._disable_chip_select()
        await asyncio.sleep(self.config['bit_time'])
        self._enable_chip_select()
        await asyncio.sleep(self.config['bit_time'])

        read_bits = 0
        for _ in range(bits):
            # read in bits on clk high
            read_bits <<= 1
            if self.config['miso_pin'].state:
                read_bits |= 0x1

            self.config['clock_pin'].pulse(int(self.config['clock_time']))
            await asyncio.sleep(self.config['bit_time'])

        self._disable_chip_select()
        return read_bits

    async def _run(self):
        while True:
            inputs = await self.read_spi(self.config['inputs'])
            for i in range(self.config['inputs']):
                num = str(i)
                if num in self._switch_states and self._switch_states[num] != bool(inputs & (1 << i)):
                    self._switch_states[num] = bool(inputs & (1 << i))
                    self.machine.switch_controller.process_switch_by_num(str(i), bool(inputs & (1 << i)), self)
