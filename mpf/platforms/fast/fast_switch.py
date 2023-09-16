"""A switch connected to a FAST controller."""
import logging

from mpf.core.utility_functions import Util
from dataclasses import dataclass
from copy import copy


MYPY = False

@dataclass
class FastSwitchConfig:
    number: str          # '00'-'68'
    mode: str            # '00'-'02'
    debounce_close: str  # '00'-'FF'
    debounce_open: str   # '00'-'FF'


class FASTSwitch:

    """A switch connected to a FAST controller."""

    # __slots__ = ["log", "connection", "send", "platform_settings", "_configured_debounce"]

    def __init__(self, communicator, hw_number, ) -> None:
        """Initialise switch."""
        self.log = logging.getLogger('FAST Switch')
        self.communicator = communicator
        self.number = hw_number  # must be int to work with the rest of MPF
        self.hw_number = Util.int_to_hex_string(hw_number)  # hex version the FAST hw actually uses
        self.platform = communicator.platform  # Needed by the SwitchController

        # self.baseline_mpf_config = None  # settings from this switch in the machine config
        # # name, invert, debounce
        # self.platform_settings = None  # platform-specific settings from the machine config
        # # debounce_open, debounce_close

        self.baseline_switch_config = FastSwitchConfig(number=self.hw_number, mode='00', debounce_close='00',
                                                       debounce_open='00')
        self.current_hw_config = self.baseline_switch_config

        # self.hw_config_good = False

    def set_initial_config(self, mpf_config, platform_settings):

        self.current_hw_config = self.convert_mpf_config_to_fast(mpf_config, platform_settings)
        self.baseline_fast_config = copy(self.current_hw_config)

    def convert_mpf_config_to_fast(self, mpf_config, platform_settings) -> FastSwitchConfig:

        debounce_close, debounce_open = self.reconcile_debounce(mpf_config, platform_settings)

        if mpf_config.invert:
            mode = '02'
        else:
            mode = '01'

        return FastSwitchConfig(number=self.hw_number, mode=mode, debounce_close=debounce_close,
                                debounce_open=debounce_open)

    def send_config_to_switch(self):

        msg = (f'{self.communicator.switch_cmd}:{self.current_hw_config.number},'
               f'{self.current_hw_config.mode},{self.current_hw_config.debounce_close},'
               f'{self.current_hw_config.debounce_open}')

        self.communicator.send_with_confirmation(msg, f'{self.communicator.switch_cmd}:P')

    def get_current_config(self):
        return (f'{self.communicator.switch_cmd}:{self.current_hw_config.number},'
               f'{self.current_hw_config.mode},{self.current_hw_config.debounce_close},'
               f'{self.current_hw_config.debounce_open}')

    def get_board_name(self):
        """Return the board of this switch."""
        if self.communicator.platform.is_retro:
            return f"FAST Retro ({self.communicator.platform.machine_type.upper()})"

        switch_index = 0
        number = Util.hex_string_to_int(self.number)
        for board_obj in self.communicator.platform.io_boards.values():
            if switch_index <= number < switch_index + board_obj.switch_count:
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
