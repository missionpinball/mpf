"""A switch connected to a FAST controller."""
import logging
from copy import copy
from dataclasses import dataclass

from mpf.core.utility_functions import Util

MYPY = False

@dataclass
class FastSwitchConfig:
    number: str          # '00'-'68'
    mode: str            # '00'-'02'
    debounce_close: str  # '00'-'FF'
    debounce_open: str   # '00'-'FF'


class FASTSwitch:

    """A switch connected to a FAST controller."""

    __slots__ = ["log", "communicator", "number", "hw_number", "platform", "baseline_switch_config",
                 "current_hw_config"]

    def __init__(self, communicator, hw_number, ) -> None:
        """initialize switch."""

        self.log = logging.getLogger('FAST Switch')
        self.communicator = communicator
        self.number = hw_number  # must be int to work with the rest of MPF
        self.hw_number = Util.int_to_hex_string(hw_number)  # hex version the FAST hw actually uses
        self.platform = communicator.platform  # Needed by the SwitchController

        self.baseline_switch_config = FastSwitchConfig(number=self.hw_number, mode='00', debounce_close='00',
                                                       debounce_open='00')
        self.current_hw_config = self.baseline_switch_config

    def set_initial_config(self, mpf_config, platform_settings):
        """Takes the mpf_config and platform_settings and converts them to the FAST format.
        Sets that to the current config and establishes it as the baseline. This is only called
        when MPF is starting up."""

        self.current_hw_config = self.convert_mpf_config_to_fast(mpf_config, platform_settings)
        self.baseline_switch_config = copy(self.current_hw_config)

    def convert_mpf_config_to_fast(self, mpf_config, platform_settings) -> FastSwitchConfig:
        """Converts the MPF switch config to the FAST format."""

        debounce_close, debounce_open = self.reconcile_debounce(mpf_config, platform_settings)

        if mpf_config.invert:
            mode = '02'
        else:
            mode = '01'

        return FastSwitchConfig(number=self.hw_number, mode=mode, debounce_close=debounce_close,
                                debounce_open=debounce_open)

    def send_config_to_switch(self):
        """Sends the current config to the switch. e.g. actually updates the physical switch."""

        msg = (f'{self.communicator.SWITCH_CMD}:{self.current_hw_config.number},'
               f'{self.current_hw_config.mode},{self.current_hw_config.debounce_close},'
               f'{self.current_hw_config.debounce_open}')

        self.communicator.send_with_confirmation(msg, f'{self.communicator.SWITCH_CMD}:P')

    def get_current_config(self):
        return (f'{self.communicator.SWITCH_CMD}:{self.current_hw_config.number},'
               f'{self.current_hw_config.mode},{self.current_hw_config.debounce_close},'
               f'{self.current_hw_config.debounce_open}')

    def get_board_name(self):
        """Return the board of this switch."""

        switch_index = 0
        for board_obj in self.communicator.platform.io_boards.values():
            if switch_index <= self.number < switch_index + board_obj.switch_count:
                return f"FAST Board {str(board_obj.node_id)}"
            switch_index += board_obj.switch_count

        # fall back if not found
        return "FAST Unknown Board"

    def reconcile_debounce(self, config, platform_settings):
        """Looks at all the possible debounce settings for the switch, the platfor, and FAST overrides and returns
        the final debounce settings for the switch.

        Returns a tuple of (debounce_open, debounce_close) in hex string format."""

        # Set the debounce from the generic true/false first, then override if the platform settings have specific values
        if config.debounce in ['normal', 'auto']:
            debounce_open = self.communicator.config['default_normal_debounce_open']
            debounce_close = self.communicator.config['default_normal_debounce_close']
        else:
            debounce_open = self.communicator.config['default_quick_debounce_open']
            debounce_close = self.communicator.config['default_quick_debounce_close']

        if 'debounce_open' in platform_settings and platform_settings['debounce_open'] is not None:
            debounce_open = platform_settings['debounce_open']

        if 'debounce_close' in platform_settings and platform_settings['debounce_close'] is not None:
            debounce_close = platform_settings['debounce_close']

        return Util.int_to_hex_string(debounce_close), Util.int_to_hex_string(debounce_open)
