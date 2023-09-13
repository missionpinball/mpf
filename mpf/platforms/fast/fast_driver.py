"""A driver/coil in the fast platform."""
from copy import copy
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from mpf.core.platform import DriverConfig
from mpf.core.utility_functions import Util
from mpf.exceptions.config_file_error import ConfigFileError
from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.platforms.fast.fast import FastHardwarePlatform    # pylint: disable-msg=cyclic-import,unused-import

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

    # __slots__ = ["log", "autofire", "_autofire_cleared", "config_state", "machine", "platform", "driver_settings",
    #              "send", "platform_settings"]

    def __init__(self, communicator: FastSerialCommunicator, hw_number: int) -> None:
        """Initialize the driver object.

        This is called once for each physical driver on the connected hardware, regardless of whether it's configured in MPF.
        """
        self.log = logging.getLogger('FAST Driver')
        self.communicator = communicator
        self.number = hw_number  # must be int to work with the rest of MPF
        self.hw_number = Util.int_to_hex_string(hw_number)  # hex version the FAST hw actually uses
        self.autofire_config = None

        self.baseline_driver_config = FastDriverConfig(number=self.hw_number, trigger='00',
                                                       switch_id='00', mode='00',
                                                       param1='00', param2='00', param3='00',
                                                       param4='00', param5='00')
        self.current_driver_config = self.baseline_driver_config

    def set_initial_config(self, mpf_config: DriverConfig, platform_settings):
        """Sets the initial config for this driver based on the MPF config.

        Args:
            mpf_config: DriverConfig instance which holds the MPF DriverConfig settings for this driver from the config file. This already incorporates
                any machine-wide defaults, etc. so it's ready to go.
            platform_settings: FastDriverConfig instance which holds any platform_settings: entries for this driver from the config file.

        This method does not actually write the config to the driver. Is just figures out what the FastDriverConfig should be.

        This will not be called for drivers that are not in the MPF config.
        """

        self.current_driver_config = self.convert_mpf_config_to_fast(mpf_config, platform_settings)
        self.baseline_driver_config = copy(self.current_driver_config)

    def convert_mpf_config_to_fast(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        """Convert an MPF config to FAST."""

        # mpf_config:
            # class DriverConfig:
            #     name: str
            #     default_pulse_ms: int
            #     default_pulse_power: float
            #     default_hold_power: float
            #     default_timed_enable_ms: int
            #     default_recycle: bool
            #     max_pulse_ms: int
            #     max_pulse_power: float
            #     max_hold_power: float
            #     pulse_with_timed_enable: bool

        # platform_settings:
            # recycle_ms: single|ms|None
            # pwm2_ms: single|ms|None

        # Mode 00 - Disable
        # Mode 10 - Pulse
        # Mode 12 - Pulse + Kick
        # Mode 18 - Pulse + Hold

        # if mpf_config.default_timed_enable_ms:  # Pulse + Hold
        #     return self.convert_to_mode_18(mpf_config, platform_settings)

        if mpf_config.default_recycle is not None:
            raise ConfigFileError(f"FAST platform does not support default_recycle for coils. Use recycle_ms instead. Coil '{mpf_config.name}'.", 7, self.log.name)

        if mpf_config.pulse_with_timed_enable:
            raise ConfigFileError(f"FAST platform does not support pulse_with_timed_enable for coils. Use pwm2_ms instead. Coil '{mpf_config.name}'.", 7, self.log.name)

        if mpf_config.default_pulse_ms > 255:
            raise ConfigFileError(f"FAST platform does not support default_pulse_ms > 255. Use pwm2_ms instead which goes up to 25,500ms. Coil '{mpf_config.name}'.", 7, self.log.name)

        if platform_settings['pwm2_ms'] and platform_settings['pwm2_ms'] > 255:
            return self.convert_to_mode_70(mpf_config, platform_settings)

        else:
            return self.convert_to_mode_10(mpf_config, platform_settings)

    def convert_to_mode_10(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        # Pulse
        # DL:<driver>,<trigger>,<switch>,10,<pwm1_ms>,<pwm1_power>,<pwm2_ms>,<pwm2_power>,<rest_ms>

        pwm2_ms, pwm2_power, recycle_ms = self._get_platform_settings(mpf_config, platform_settings)

        return FastDriverConfig(number = self.hw_number,
                                trigger='81',
                                switch_id='00',
                                mode='10',
                                param1=Util.int_to_hex_string(mpf_config.default_pulse_ms),  # pwm1_ms
                                param2=Util.float_to_pwm8_hex_string(mpf_config.default_pulse_power),  # pwm1_power
                                param3=Util.int_to_hex_string(pwm2_ms),  # pwm2_ms
                                param4=Util.float_to_pwm8_hex_string(pwm2_power),  # pwm2_power
                                param5=Util.int_to_hex_string(recycle_ms))  # rest_ms

    def convert_to_mode_18(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        # Pulse + Hold
        # DL:<driver>,<trigger>,<switch>,18,<pwm1_ms>,<pwm1_power>,<pwm2_power>,<rest_ms>,<n/a>

        _, pwm2_power, recycle_ms = self._get_platform_settings(mpf_config, platform_settings)

        return FastDriverConfig(number = self.hw_number,
                                trigger='81',
                                switch_id='00',
                                mode='18',
                                param1=Util.int_to_hex_string(mpf_config.default_pulse_ms),  # pwm1_ms
                                param2=Util.float_to_pwm8_hex_string(mpf_config.default_pulse_power),  # pwm1_power
                                param3=Util.float_to_pwm8_hex_string(pwm2_power),  # pwm2_power
                                param4=Util.int_to_hex_string(recycle_ms),
                                param5='00')  # na

    def convert_to_mode_70(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        # Long Pulse
        # DL:<driver_id>,<trigger>,<switch_id>,<70>,<PWM1_ONTIME>,<PWM1>,<PWM2_ONTIMEx100ms>,<PWM2>,<REST_TIME><CR>

        _, pwm2_power, recycle_ms = self._get_platform_settings(mpf_config, platform_settings)

        pwm2_ms = platform_settings['pwm2_ms'] // 100

        return FastDriverConfig(number = self.hw_number,
                                trigger='81',
                                switch_id='00',
                                mode='70',
                                param1=Util.int_to_hex_string(mpf_config.default_pulse_ms),  # pwm1_ms
                                param2=Util.float_to_pwm8_hex_string(mpf_config.default_pulse_power),  # pwm1_power
                                param3=Util.int_to_hex_string(pwm2_ms),  # pwm2_ms * 100ms
                                param4=Util.float_to_pwm8_hex_string(pwm2_power),  # pwm2_power
                                param5=Util.int_to_hex_string(recycle_ms))  # rest_ms

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

        msg = (f'{self.communicator.driver_cmd}:{self.hw_number},{trigger},'
               f'{self.current_driver_config.switch_id},{self.current_driver_config.mode},{self.current_driver_config.param1},'
               f'{self.current_driver_config.param2},{self.current_driver_config.param3},{self.current_driver_config.param4},'
               f'{self.current_driver_config.param5}')
        if wait_to_confirm:
            self.communicator.send_with_confirmation(msg, f'{self.communicator.driver_cmd}')
        else:
            self.communicator.send_and_forget(msg)

    def get_board_name(self):
        # This code is duplicated, TODO
        """Return the board of this driver."""
        if self.communicator.platform.is_retro:
            return f"FAST Retro ({self.communicator.platform.machine_type.upper()})"

        coil_index = 0
        number = Util.hex_string_to_int(self.number)
        for board_obj in self.communicator.platform.io_boards.values():
            if coil_index <= number < coil_index + board_obj.driver_count:
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
        """Reset a driver."""
        self.log.debug("Resetting driver %s", self.driver_settings)

        cmd = f'{self.communicator.driver_cmd}:{self.hw_number},00,00,00,00,00,00,00,00'

        self.communicator.send_with_confirmation(cmd, self.communicator.driver_cmd)

    def disable(self):
        """Disable (turn off) this driver."""
        self.communicator.send_and_forget(f'{self.communicator.trigger_cmd}:{self.hw_number},02')
        self._reenable_autofire_if_configured()

        # reenable the autofire
        if self.autofire_config:
            cmd = f'{self.communicator.trigger_cmd}:{self.hw_number},00'
            self.log.debug("Re-enabling autofire mode: %s", cmd)
            self.communicator.send_and_forget(cmd)

    def set_autofire_pulse(self, pulse_settings, switch):
        reconfigured = False
        mode = self.current_driver_config.mode

        pwm1_ms = Util.int_to_hex_string(pulse_settings.duration)
        pwm1_power = Util.float_to_pwm8_hex_string(pulse_settings.power)

        if self.current_driver_config.param1 != pwm1_ms:
            self.current_driver_config.param1 = pwm1_ms
            reconfigured = True

        if self.current_driver_config.param2 != pwm1_power:
            self.current_driver_config.param2 = pwm1_power
            reconfigured = True

        if self.current_driver_config.switch_id != switch.hw_switch.hw_number:
            self.current_driver_config.switch_id = switch.hw_switch.hw_number
            reconfigured = True
        # TODO TL can update the switch, if that's all we need, don't send a new config

        trigger = '01'

        if switch.invert:
            trigger = self.set_bit(trigger, 4)

        if self.current_driver_config.trigger != trigger:
            self.current_driver_config.trigger = trigger
            reconfigured = True

        if not reconfigured:
            # Set the driver to automatic using the existing configuration
            self.communicator.send_and_forget(f'{self.communicator.trigger_cmd}:{self.hw_number},00')
            return

        else:  # Send a new driver config
            self.send_config_to_driver(one_shot=False)

        self.autofire_config = copy(self.current_driver_config)

    def clear_autofire(self, config_cmd, number):
        """Clear autofire."""
        raise AssertionError("Not implemented")
        cmd = '{}{},81'.format(config_cmd, number)
        self.log.debug("Clearing hardware rule: %s", cmd)
        self.communicator.send_with_confirmation(cmd, self.communicator.driver_cmd)
        self.autofire = None
        self.config_state = None

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this driver."""

        reconfigured = False
        mode = self.current_driver_config.mode

        pwm1_ms = Util.int_to_hex_string(pulse_settings.duration)
        pwm1_power = Util.float_to_pwm8_hex_string(pulse_settings.power)
        pwm2_power = Util.float_to_pwm8_hex_string(hold_settings.power)

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
            self.communicator.send_and_forget(f'{self.communicator.trigger_cmd}:{self.hw_number},03')
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
            self.communicator.send_and_forget(f'{self.communicator.trigger_cmd}:{self.hw_number},01')
            return

        else:  # Send a new driver config and also trigger it now
            self.send_config_to_driver(one_shot=True)
            self._reenable_autofire_if_configured()

    def _reenable_autofire_if_configured(self):
        """Reenable autofire if configured."""
        if self.autofire_config and self.autofire_config != self.current_driver_config:
            self.log.debug("Re-enabling autofire mode")
            self.current_driver_config = copy(self.autofire_config)
            self.send_config_to_driver()
