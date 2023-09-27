"""A driver/coil in the FAST platform."""
import logging
from copy import copy
from dataclasses import dataclass

from mpf.core.platform import DriverConfig
from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.fast.fast import \
        FastHardwarePlatform  # pylint: disable-msg=cyclic-import,unused-import

@dataclass
class FastDriverConfig:
    number: str
    trigger: str
    switch_id: str
    mode: str
    param1: str
    param2: str
    param3: str
    param4: str
    param5: str

class FASTDriver:

    """Base class for drivers connected to a FAST Controller."""

    __slots__ = ["log", "communicator", "number", "hw_number", "autofire_config", "baseline_driver_config",
                 "current_driver_config", "mode_param_mapping", "platform_settings"]

    def __init__(self, communicator: FastSerialCommunicator, hw_number: int) -> None:
        """Initialize the driver object.

        This is called once for each physical driver on the connected hardware, regardless of whether it's configured in MPF.
        """
        self.log = logging.getLogger('FAST Driver')
        self.communicator = communicator
        self.number = hw_number  # must be int to work with the rest of MPF
        self.hw_number = Util.int_to_hex_string(hw_number)  # hex version the FAST hw actually uses
        self.autofire_config = None
        self.platform_settings = dict()

        self.baseline_driver_config = FastDriverConfig(number=self.hw_number, trigger='00',
                                                       switch_id='00', mode='00',
                                                       param1='00', param2='00', param3='00',
                                                       param4='00', param5='00')
        self.current_driver_config = self.baseline_driver_config

        self.mode_param_mapping = {
            '10': ['pwm1_ms', 'pwm1_power', 'pwm2_ms', 'pwm2_power', 'recycle_ms'],
            '12': ['pwm1_ms', 'pwm1_power', 'pwm2_ms', 'pwm2_power', 'kick_ms'],
            '18': ['pwm1_ms', 'pwm1_power', 'pwm2_power', 'recycle_ms', None],
            '20': ['off_switch', 'pwm1_ms', 'pwm1_power', 'pwm2_power', 'rest_ms'],
            '30': ['delay_ms_x10', 'pwm1_ms', 'pwm2_ms', 'pwm2_power', 'recycle_ms'],
            '70': ['pwm1_ms', 'pwm1_power', 'pwm2_ms_x100', 'pwm2_power', 'recycle_ms'],
            '75': ['off_switch', 'pwm1_ms', 'pwm2_ms_x100', 'pwm2_power', 'recycle_ms'],
        }

    def set_initial_config(self, mpf_config: DriverConfig, platform_settings):
        """Sets the initial config for this driver based on the MPF config.

        Args:
            mpf_config: DriverConfig instance which holds the MPF DriverConfig settings for this driver from the config file. This already incorporates
                any machine-wide defaults, etc. so it's ready to go.
            platform_settings: FastDriverConfig instance which holds any platform_settings: entries for this driver from the config file.

        This method does not actually write the config to the driver. Is just figures out what the FastDriverConfig should be.

        This will not be called for drivers that are not in the MPF config.
        """

        self.platform_settings = platform_settings
        self.current_driver_config = self.convert_mpf_config_to_fast(mpf_config, platform_settings)
        self.baseline_driver_config = copy(self.current_driver_config)

    def convert_mpf_config_to_fast(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        """Convert a DriverConfig (used throughout MPF) to FastDriverConfig (FAST specific version).
        This is only used for the initial configuration of drivers. Autofire rules update these."""

        if mpf_config.default_recycle:
            raise ConfigFileError(f"FAST platform does not support default_recycle for coils. Use platform_settings:recycle_ms instead. Coil '{mpf_config.name}'.", 7, self.log.name)

        if mpf_config.default_pulse_ms > 255:
            raise ConfigFileError(f"FAST platform does not support default_pulse_ms > 255. Use platform_settings:pwm2_ms instead which goes up to 25,500ms. Coil '{mpf_config.name}'.", 7, self.log.name)

        pwm2_ms, pwm2_power, recycle_ms = self._get_platform_settings(mpf_config, platform_settings)

        if platform_settings['pwm2_ms'] and platform_settings['pwm2_ms'] > 255:
            mode = '70'
            pwm2_ms = platform_settings['pwm2_ms'] // 100
        else:
            mode = '10'

        return FastDriverConfig(number = self.hw_number,
                                trigger='81',
                                switch_id='00',
                                mode=mode,
                                param1=Util.int_to_hex_string(mpf_config.default_pulse_ms),
                                param2=Util.float_to_pwm8_hex_string(mpf_config.default_pulse_power),
                                param3=Util.int_to_hex_string(pwm2_ms),
                                param4=Util.float_to_pwm8_hex_string(pwm2_power),
                                param5=Util.int_to_hex_string(recycle_ms))

    def _get_platform_settings(self, mpf_config: DriverConfig, platform_settings):
        if platform_settings['pwm2_ms'] is not None:
            pwm2_ms = platform_settings['pwm2_ms']
        else:
            pwm2_ms = 0

        if mpf_config.default_hold_power is not None:
            pwm2_power = mpf_config.default_hold_power
        else:
            pwm2_power = 0

        if platform_settings['recycle_ms'] is not None:
            recycle_ms = platform_settings['recycle_ms']
        else:
            recycle_ms = 0  # mpf_config.default_recycle is a bool and not well defined, so we ignore it in the FAST platform

        return pwm2_ms, pwm2_power, recycle_ms

    def set_bit(self, hex_string, bit):
        """Sets a bit in a hex string.

        Args:
            hex_string (_type_): Hex string, e.g. '81'
            bit (_type_): Bit to set, e.g. 3

        Returns:
            _type_: Returns the hex string with the bit set, e.g. '89'
        """
        num = int(hex_string, 16)
        num |= 1 << bit
        return Util.int_to_hex_string(num)

    def clear_bit(self, hex_string, bit):
        num = int(hex_string, 16)
        num &= ~(1 << bit)
        return Util.int_to_hex_string(num)

    def send_config_to_driver(self, one_shot: bool = False, wait_to_confirm: bool = False):

        if one_shot:
            trigger = self.set_bit(self.current_driver_config.trigger, 3)
        else:
            trigger = self.current_driver_config.trigger

        msg = (f'{self.communicator.DRIVER_CMD}:{self.hw_number},{trigger},'
               f'{self.current_driver_config.switch_id},{self.current_driver_config.mode},{self.current_driver_config.param1},'
               f'{self.current_driver_config.param2},{self.current_driver_config.param3},{self.current_driver_config.param4},'
               f'{self.current_driver_config.param5}')
        if wait_to_confirm:
            self.communicator.send_with_confirmation(msg, f'{self.communicator.DRIVER_CMD}')
        else:
            self.communicator.send_and_forget(msg)

    def get_current_config(self):
        return (f'{self.communicator.DRIVER_CMD}:{self.hw_number},{self.current_driver_config.trigger},'
               f'{self.current_driver_config.switch_id},{self.current_driver_config.mode},{self.current_driver_config.param1},'
               f'{self.current_driver_config.param2},{self.current_driver_config.param3},{self.current_driver_config.param4},'
               f'{self.current_driver_config.param5}')

    def get_board_name(self):
        """Return the board of this driver."""

        coil_index = 0
        for board_obj in self.communicator.platform.io_boards.values():
            if coil_index <= self.number < coil_index + board_obj.driver_count:
                return f"FAST Board {str(board_obj.node_id)}"
            coil_index += board_obj.driver_count

        # fall back if not found
        return "FAST Unknown Board"

    def get_recycle_ms_for_cmd(self, recycle, pulse_ms):
        """Return recycle ms."""
        if not recycle:
            return "00"
        if self.platform_settings.get('recycle_ms') is not None:
            return Util.int_to_hex_string(self.platform_settings['recycle_ms'])

        # default recycle_ms to pulse_ms * 2
        if pulse_ms * 2 > 255:
            return "FF"

        return Util.int_to_hex_string(pulse_ms * 2)

    @classmethod
    def get_control_for_cmd(cls, switch1, switch2=None):
        """Return control bytes."""
        control = 0x01  # Driver enabled
        if switch1.invert:
            control += 0x10
        if switch2 and switch2.invert:
            control += 0x20

        return Util.int_to_hex_string(int(control))

    async def reset(self):
        """Reset the driver to fresh (disabled/unconfigured) state."""

        self.current_driver_config.trigger =   '00'
        self.current_driver_config.switch_id = '00'
        self.current_driver_config.mode =      '00'
        self.current_driver_config.param1 =    '00'
        self.current_driver_config.param2 =    '00'
        self.current_driver_config.param3 =    '00'
        self.current_driver_config.param4 =    '00'
        self.current_driver_config.param5 =    '00'

        await self.communicator.send_and_wait_for_response_processed(self.get_current_config(), self.get_current_config())

    def disable(self):
        """Disable (turn off) this driver."""
        if not self._reenable_autofire_if_configured():
            self.communicator.send_and_forget(f'{self.communicator.TRIGGER_CMD}:{self.hw_number},02')

    def set_hardware_rule(self, mode, switch, coil_settings, **kwargs):

        self._check_switch_coil_combination(switch, coil_settings.hw_driver)

        reconfigured = False
        trigger_needed = False
        switch_needed = False

        if not mode:
            mode = self.current_driver_config.mode

        new_settings = kwargs
        new_settings['pwm1_ms'] = Util.int_to_hex_string(coil_settings.pulse_settings.duration)
        new_settings['pwm1_power'] = Util.float_to_pwm8_hex_string(coil_settings.pulse_settings.power)

        if coil_settings.hold_settings:
            new_settings['pwm2_power'] = Util.float_to_pwm8_hex_string(coil_settings.hold_settings.power)

            if coil_settings.hold_settings.duration and coil_settings.hold_settings.duration <= 255:
                new_settings['pwm2_ms'] = Util.int_to_hex_string(coil_settings.hold_settings.duration,
                                                                 allow_overflow=True)
        else:
            # If there are no new hold settings, we want to use the existing ones since they could have been
            # configured via other commands which support more settings than these rules
            new_settings['pwm2_power'] = None
            new_settings['pwm2_ms'] = None

        if coil_settings.recycle is True:
            if self.platform_settings['recycle_ms']:  # MPF autofire rules will use True, so pull it from the config if specified.
                new_settings['recycle_ms'] = Util.int_to_hex_string(self.platform_settings['recycle_ms'])
            else:
                new_settings['recycle_ms'] = '00'
        elif not coil_settings.recycle:  # False or None
            new_settings['recycle_ms'] = '00'
        else:
            new_settings['recycle_ms'] = Util.int_to_hex_string(coil_settings.recycle)

        # Update the current_driver_config with any new settings
        for idx, param in enumerate(self.mode_param_mapping[mode]):
            if param is None or new_settings.get(param, None) is None:
                continue
            if param == 'delay_ms_x10':
                new_settings['delay_ms'] = Util.int_to_hex_string(int(new_settings[param], 16) // 10)
            elif param == 'pwm2_ms_x100':
                new_settings['pwm2_ms'] = Util.int_to_hex_string(int(new_settings[param], 16) // 100)

            param_name = f'param{idx+1}'
            if new_settings[param] != getattr(self.current_driver_config, param_name):
                setattr(self.current_driver_config, param_name, new_settings[param])
                reconfigured = True

        if self.current_driver_config.switch_id != switch.hw_switch.hw_number:
            self.current_driver_config.switch_id = switch.hw_switch.hw_number
            trigger_needed = True
            switch_needed = True

        if self.current_driver_config.mode != mode:
            self.current_driver_config.mode = mode
            reconfigured = True

        trigger = '01'

        if switch.invert:
            trigger = self.set_bit(trigger, 4)

        if self.is_new_config_needed(self.current_driver_config.trigger, trigger):
            reconfigured = True
        elif trigger != self.current_driver_config.trigger:
            trigger_needed = True

        self.current_driver_config.trigger = trigger
        self.autofire_config = copy(self.current_driver_config)

        if reconfigured:  # Send a new driver config
            self.send_config_to_driver(one_shot=False)
        elif trigger_needed:  # We only need to update the triggers
            # Set the driver to automatic using the existing configuration
            if switch_needed:
                self.communicator.send_and_forget(f'{self.communicator.TRIGGER_CMD}:{self.hw_number},00,{switch.hw_switch.hw_number}')
            else:
                self.communicator.send_and_forget(f'{self.communicator.TRIGGER_CMD}:{self.hw_number},00')

    def _check_switch_coil_combination(self, switch, coil):
        # TODO move this to the communicator or something? Since it's only Nano?

        # V2 hardware can write rules across node boards
        if self.communicator.config['controller'] != 'nano':
            return

        # first 8 switches always work
        if 0 <= switch.hw_switch.number <= 7:
            return

        if self.get_board_name() != switch.hw_switch.get_board_name():
            raise AssertionError(f"Driver {coil.number} and switch {switch.hw_switch.number} "
                                "are on different boards. Cannot apply rule!")

    def is_new_config_needed(self, current, new):
        # figures out if bits other than 6 and 7 changed, meaning we need a full new DL command not just TL update
        current_num = int(current, 16)
        new_num = int(new, 16)
        bitmask = 0x3F  # 0011 1111 in binary

        # Use bitwise AND to mask out bits 6 and 7
        current_num &= bitmask
        new_num &= bitmask

        return current_num != new_num

    def clear_autofire(self):
        """Clear autofire."""
        self._check_and_clear_delay()
        if not self.autofire_config:
            return

        # TL control code 2 sets bit 7 and clears 6
        self.current_driver_config.trigger = self.clear_bit(self.current_driver_config.trigger, 6)
        self.current_driver_config.trigger = self.set_bit(self.current_driver_config.trigger, 7)

        self.autofire_config = None
        self.communicator.send_and_forget(f'{self.communicator.TRIGGER_CMD}:{self.hw_number},02')

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this driver."""

        self._check_and_clear_delay()

        reconfigured = False
        mode = self.current_driver_config.mode

        pwm1_ms = Util.int_to_hex_string(pulse_settings.duration)
        pwm1_power = Util.float_to_pwm8_hex_string(pulse_settings.power)
        pwm2_power = Util.float_to_pwm8_hex_string(hold_settings.power)

        if mode != '18':
            mode = '18'
            reconfigured = True

        if self.current_driver_config.param1 != pwm1_ms:
            self.current_driver_config.param1 = pwm1_ms
            reconfigured = True

        if self.current_driver_config.param2 != pwm1_power:
            self.current_driver_config.param2 = pwm1_power
            reconfigured = True

        if self.current_driver_config.param3 != pwm2_power:
            self.current_driver_config.param3 = pwm2_power
            reconfigured = True

        if self.current_driver_config.param4 != '00':
            self.current_driver_config.param4 = '00'
            reconfigured = True

        if self.current_driver_config.mode != '18':
            self.current_driver_config.mode = '18'
            reconfigured = True

        if not reconfigured:
            # Trigger the driver directly using the existing configuration
            self.communicator.send_and_forget(f'{self.communicator.TRIGGER_CMD}:{self.hw_number},03')
            return
        else:  # Send a new driver config and also trigger it now
            self.current_driver_config.trigger = 'C1'
            self.send_config_to_driver(one_shot=False)

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and hold this driver for a specified duration."""

        if not hold_settings.duration and self.current_driver_config.mode == '70':
            # If we are in mode 70, timed enable defaults are already set
            hold_settings = None

        self._pulse(pulse_settings, hold_settings)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse this driver."""
        self._pulse(pulse_settings)

    def _pulse(self, pulse_settings: PulseSettings, hold_settings: HoldSettings = None):
        """Pulse this driver, with an optional hold setting.

        The FAST platform supports pulse and hold configuration in the same command, so
        this method can be used for both pulse() and timed_enable() behavior.
        """

        reconfigured = False
        mode = self.current_driver_config.mode

        # This method current hardcodes the params but some modes use different orders
        # The workaround for now is to just set the mode to 10.
        # No real downside, it will just send a full DL command instead of a TL
        # TODO elegant future implementation would be to use the mode_param_mapping to use the current configured mode

        if mode not in ['10', '12', '18', '70']:
            mode = '10'
            reconfigured = True

        pwm1_ms = Util.int_to_hex_string(pulse_settings.duration)
        pwm1_power = Util.float_to_pwm8_hex_string(pulse_settings.power)

        if self.current_driver_config.param1 != pwm1_ms:
            self.current_driver_config.param1 = pwm1_ms
            reconfigured = True

        if self.current_driver_config.param2 != pwm1_power:
            self.current_driver_config.param2 = pwm1_power
            reconfigured = True

        if hold_settings is not None:
            if hold_settings.duration > 25500:
                raise AssertionError("FAST platform does not support hold durations > 25500ms")
            elif 25500 >= hold_settings.duration > 255:
                hold_ms = Util.int_to_hex_string(hold_settings.duration // 100)
                mode = '70'
            elif 255 >= hold_settings.duration >= 0:
                hold_ms = Util.int_to_hex_string(hold_settings.duration)
                mode = '10'

            hold_power = Util.float_to_pwm8_hex_string(hold_settings.power)

        else:
            hold_ms = self.current_driver_config.param3
            hold_power = self.current_driver_config.param4

        if self.current_driver_config.mode != mode:
            self.current_driver_config.mode = mode
            reconfigured = True

        if self.current_driver_config.param3 != hold_ms:
            self.current_driver_config.param3 = hold_ms
            reconfigured = True

        if self.current_driver_config.param4 != hold_power:
            self.current_driver_config.param4 = hold_power
            reconfigured = True

        if not reconfigured:
            # Trigger the driver directly using the existing configuration
            self.communicator.send_and_forget(f'{self.communicator.TRIGGER_CMD}:{self.hw_number},01')
        else:  # Send a new driver config and also trigger it now
            self.send_config_to_driver(one_shot=True)

        # reset not add so we keep on kicking this delay down the road if we keep getting pulses
        self.communicator.machine.delay.reset(pulse_settings.duration + 1, self._reenable_autofire_if_configured,
                                              f'fast_driver_{self.number}_delay')

    def _reenable_autofire_if_configured(self):
        """Reenable autofire if configured.

        Returns True if autofire was reenabled, False otherwise."""
        self._check_and_clear_delay()
        if self.autofire_config and self.autofire_config != self.current_driver_config:
            self.log.debug("Re-enabling autofire mode")
            self.current_driver_config = copy(self.autofire_config)
            self.send_config_to_driver()
            return True
        return False

    def _check_and_clear_delay(self):
        """Check if we have a delay and clear it."""
        self.communicator.machine.delay.remove(f'fast_driver_{self.number}_delay')