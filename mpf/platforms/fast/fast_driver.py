"""A driver/coil in the fast platform."""
from copy import copy
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from mpf.core.platform import DriverConfig
from mpf.core.utility_functions import Util
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

        self.baseline_driver_config = FastDriverConfig(number=self.hw_number, trigger='00', switch_id='00', mode='00',
                                                 param1='00', param2='00', param3='00', param4='00', param5='00')
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

        # platform_settings:
            # recycle_ms: single|ms|None
            # pwm2_ms: single|ms|None
            # pwm2_power: single|float(0,1)|None

        # Mode 00 - Disable
        # Mode 10 - Pulse
        # Mode 12 - Pulse + Kick
        # Mode 18 - Pulse + Hold

        if mpf_config.default_timed_enable_ms:  # Pulse + Hold
            return self.convert_to_mode_18(mpf_config, platform_settings)

        # if mpf_config.default_pulse_ms > 255:  # Long Pulse
        #     return self.convert_to_mode_70(mpf_config, platform_settings)

        # regular pulse or long pulse TODO verify long pulse will be re-upped
        return self.convert_to_mode_10(mpf_config, platform_settings)


    def convert_to_mode_10(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        # DL:<driver>,<trigger>,<switch>,10,<pwm1_ms>,<pwm1_power>,<pwm2_ms>,<pwm2_power>,<rest_ms>

        pwm2_ms, pwm2_power, recycle_ms = self._get_platform_settings(mpf_config, platform_settings)

        if mpf_config.default_pulse_ms > 255:
            pulse_ms = 255
        else:
            pulse_ms = mpf_config.default_pulse_ms

        return FastDriverConfig(number = self.hw_number,
                                trigger='81',
                                switch_id='00',
                                mode='10',
                                param1=Util.int_to_hex_string(pulse_ms),  # pwm1_ms
                                param2=Util.float_to_hex(mpf_config.default_pulse_power),  # pwm1_power
                                param3=Util.int_to_hex_string(pwm2_ms),  # pwm2_ms
                                param4=Util.float_to_pwm8_hex_string(pwm2_power),  # pwm2_power
                                param5=Util.int_to_hex_string(recycle_ms))  # rest_ms

    def convert_to_mode_18(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        # DL:<driver>,<trigger>,<switch>,18,<pwm1_ms>,<pwm1_power>,<pwm2_power>,<rest_ms>,<n/a>

        _, pwm2_power, recycle_ms = self._get_platform_settings(mpf_config, platform_settings)

        return FastDriverConfig(number = self.hw_number,
                                trigger='81',
                                switch_id='00',
                                mode='18',
                                param1=Util.int_to_hex_string(mpf_config.default_pulse_ms),  # pwm1_ms
                                param2=Util.float_to_hex(mpf_config.default_pulse_power),  # pwm1_power
                                param3=Util.float_to_pwm8_hex_string(pwm2_power),  # pwm2_power
                                param4=Util.int_to_hex_string(recycle_ms),
                                param5='00')  # na

    def convert_to_mode_70(self, mpf_config: DriverConfig, platform_settings) -> FastDriverConfig:
        # Mode 70 - Long Pulse
        # DL:<driver_id>,<trigger>,<switch_id>,<70>,<PWM1_ONTIME>,<PWM1>,<PWM2_ONTIMEx100ms>,<PWM2>,<REST_TIME><CR>
        fast_config.mode = '70'

        raise NotImplementedError

    def _get_platform_settings(self, mpf_config: DriverConfig, platform_settings):

        if platform_settings['pwm2_ms'] is not None:
            pwm2_ms = platform_settings['pwm2_ms']
        else:
            pwm2_ms = 0

        if platform_settings['pwm2_power'] is not None:
            pwm2_power = platform_settings['pwm2_power']
        else:
            pwm2_power = mpf_config.default_hold_power

        if platform_settings['recycle_ms'] is not None:
            recycle_ms = platform_settings['recycle_ms']
        else:
            recycle_ms = 0  # mpf_config.default_recycle is a bool and not well defined, so we ignore it in the FAST platform

        return pwm2_ms, pwm2_power, recycle_ms


    def send_config_to_driver(self):
        msg = (f'{self.communicator.driver_cmd}:{self.hw_number},{self.current_driver_config.trigger},'
               f'{self.current_driver_config.switch_id},{self.current_driver_config.mode},{self.current_driver_config.param1},'
               f'{self.current_driver_config.param2},{self.current_driver_config.param3},{self.current_driver_config.param4},'
               f'{self.current_driver_config.param5}')
        self.communicator.send_with_confirmation(msg, f'{self.communicator.driver_cmd}')

        # TODO save this as FastDriverConfig as the last config sent to the driver

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

    @classmethod
    def get_pwm_for_cmd(cls, power: float):
        """Return a hex string for a float power setting."""
        # use PWM8 if sufficiently accurate
        if (power * 8) - int(power * 8) < 0.025:
            return Util.pwm8_to_hex_string(int(power * 8)).upper()

        return Util.pwm32_to_hex_string(int(power * 32)).upper()

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

        cmd = f'{self.communicator.driver_cmd}:{self.number},00,00,00'

        self.communicator.send_with_confirmation(cmd, self.communicator.driver_cmd)

    def disable(self):
        """Disable (turn off) this driver."""
        cmd = f'{self.communicator.trigger_cmd}:{self.number},02'

        self.log.debug("Sending Disable Command: %s", cmd)
        self.communicator.send_and_forget(cmd)  # TODO remove config lookups

        self._reenable_autofire_if_configured()

        # reenable the autofire
        if self.autofire:
            cmd = f'{self.communicator.trigger_cmd}:{self.number},00'
            self.log.debug("Re-enabling auto fire mode: %s", cmd)
            self.communicator.send_and_forget(cmd)  # TODO remove config lookups

    def set_autofire(self, autofire_cmd, pulse_duration, pulse_power, hold_power):
        """Set an autofire."""
        self.autofire = autofire_cmd, (pulse_duration, pulse_power, hold_power)
        self.config_state = pulse_duration, pulse_power, hold_power
        self._autofire_cleared = False
        self.log.debug("Writing hardware rule: %s", autofire_cmd)
        self.communicator.send_with_confirmation(autofire_cmd, self.communicator.driver_cmd)

    def clear_autofire(self, config_cmd, number):
        """Clear autofire."""
        cmd = '{}{},81'.format(config_cmd, number)
        self.log.debug("Clearing hardware rule: %s", cmd)
        self.communicator.send_with_confirmation(cmd, self.communicator.driver_cmd)
        self.autofire = None
        self.config_state = None

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turn on) this driver."""
        config_state = pulse_settings.duration, pulse_settings.power, hold_settings.power
        if self.autofire and self.config_state == config_state:
            # If this driver is also configured for an autofire rule, we just
            # manually trigger it with the trigger_cmd and manual on ('03')
            cmd = f'{self.communicator.trigger_cmd}:{self.number},03'
        else:
            # Otherwise we send a full config command, trigger C1 (logic triggered
            # and drive now) switch ID 00, mode 18 (latched)
            self._autofire_cleared = True

            cmd = '{}:{},C1,00,18,{},{},{},{}'.format(
                self.communicator.driver_cmd,
                self.number,
                Util.int_to_hex_string(pulse_settings.duration),
                self.get_pwm_for_cmd(pulse_settings.power),
                self.get_hold_pwm_for_cmd(hold_settings.power),
                self.get_recycle_ms_for_cmd(self.baseline_mpf_config.default_recycle, pulse_settings.duration)
            )
            self.config_state = (pulse_settings.duration, pulse_settings.duration, hold_settings.power)

        self.log.debug("Sending Enable Command: %s", cmd)
        self.communicator.send_and_forget(cmd)  # TODO send_txt_with_ack

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and hold this driver for a specified duration."""
        self._pulse(pulse_settings, hold_settings)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse this driver."""
        self._pulse(pulse_settings)

    def _pulse(self, pulse_settings: PulseSettings, hold_settings: HoldSettings = None):
        """Pulse this driver, with an optional hold setting.

        The FAST platform supports pulse and hold configuration in the same command, so
        this method can be used for both pulse() and timed_enable() behavior.
        """
        hex_ms_string = Util.int_to_hex_string(pulse_settings.duration)
        if hold_settings is not None:
            hold_power = self.get_hold_pwm_for_cmd(hold_settings.power)
            hold_ms = Util.int_to_hex_string(hold_settings.duration, True)
            config_state = (pulse_settings.duration, pulse_settings.power, hold_settings.power)
        else:
            hold_power = '00'
            hold_ms = '00'
            config_state = (pulse_settings.duration, pulse_settings.power, 0)

        # reconfigure if we have to
        if not self.config_state or self.config_state[0] != config_state[0] or self.config_state[1] != config_state[1]:

            self.config_state = config_state
            self._autofire_cleared = True

            # The 89 trigger will write this rule to the driver and pulse it immediately after
            cmd = '{}:{},89,00,10,{},{},{},{},00'.format(
                self.communicator.driver_cmd,
                self.number,
                hex_ms_string,
                self.get_pwm_for_cmd(pulse_settings.power),
                hold_ms,
                hold_power
            )
            self.communicator.send_with_confirmation(cmd, self.communicator.driver_cmd)
        else:
            # Trigger the driver directly using the existing configuration
            cmd = '{}:{},01'.format(self.communicator.trigger_cmd, self.number)
            self.communicator.send_and_forget(cmd)

        # restore autofire
        self._reenable_autofire_if_configured()

        return Util.hex_string_to_int(hex_ms_string)

    def _reenable_autofire_if_configured(self):
        """Reenable autofire if configured."""
        if self.autofire and self._autofire_cleared:
            self._autofire_cleared = False
            cmd = self.autofire[0]
            self.config_state = self.autofire[1]

            self.log.debug("Re-enabling auto fire mode: %s", cmd)
            self.communicator.send_with_confirmation(cmd, self.communicator.driver_cmd)
