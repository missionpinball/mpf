"""Contains the base class for the Snux driver overlay.

This class overlays an existing WPC-compatible platform interface to work with
Mark Sunnucks's System 11 interface board.
"""
import logging
from typing import Any

from mpf.core.machine import MachineController
from mpf.platforms.system11 import System11OverlayPlatform


class SnuxHardwarePlatform(System11OverlayPlatform):

    """Overlay platform for the snux hardware board."""

    __slots__ = ["snux_config"]

    def __init__(self, machine: MachineController) -> None:
        """Initalise the board."""
        super().__init__(machine)
        self.snux_config = None         # type: Any

    def _null_log_handler(self, *args, **kwargs):
        pass

    def _initialize(self, **kwargs):
        super()._initialize(**kwargs)

        self.log.debug("Configuring Snux Diag LED for driver %s",
                       self.snux_config['diag_led_driver'].name)

        # Hack to silence logging of P_ROC
        # TODO: clean this up
        self.snux_config['diag_led_driver'].hw_driver.log.info = self._null_log_handler
        self.snux_config['diag_led_driver'].hw_driver.log.debug = self._null_log_handler

        self.snux_config['diag_led_driver'].enable()

        self.machine.events.add_handler('init_phase_5',
                                        self._initialize_phase_2)

    def _initialize_phase_2(self, **kwargs):
        del kwargs
        self.machine.clock.schedule_interval(self._flash_diag_led, 0.5)

    def _validate_config(self):
        super()._validate_config()
        self.snux_config = self.machine.config_validator.validate_config(
            'snux', self.machine.config['snux'])

    def _flash_diag_led(self):
        """Flash diagnosis LED."""
        self.snux_config['diag_led_driver'].pulse(250)
