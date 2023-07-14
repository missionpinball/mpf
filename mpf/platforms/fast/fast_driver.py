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

    def __init__(self, communicator: FastSerialCommunicator, net_version: int, hw_number: int) -> None:
        """Initialise driver."""
        self.log = logging.getLogger('FASTDriver')

        self.communicator = communicator
        self.net_version = net_version
        self.number = hw_number

        self.baseline_mpf_config = None
        self.platform_settings = None

        self.hw_config_good = False
        self.platform_settings = None
        self.autofire = None
        self.config_state = None # Tuple (pulse_ms, pulse_power, hold_power) in MPF scale

        self.hw_driver_config = FastDriverConfig(number=Util.int_to_hex_string(hw_number), trigger='00', switch_id='00', mode='00',
                                                 param1='00', param2='00', param3='00', param4='00', param5='00')

    def set_initial_config(self, mpf_config: DriverConfig, platform_settings):
        """Sets the initial config for this driver by merging the machine-wide config,
        this driver's config, the platform's default config, and any platform specific overrides.

        This method does not actually write the config to the driver.
        It does set self.hw_driver_config_good = False
        """

        # TODO add validation

        self.baseline_mpf_config = copy(mpf_config)


        self.platform_settings = platform_settings

        fast_config_from_mpf = self.convert_mpf_config_to_fast(mpf_config)

        if fast_config_from_mpf != self.hw_driver_config:
            self.hw_driver_config = fast_config_from_mpf
            self.hw_config_good = False

    def convert_mpf_config_to_fast(self, mpf_config: DriverConfig) -> FastDriverConfig:
        """Convert an MPF config to FAST."""

        # MPF config (partial):
        # allow_enable: single|bool|false
        # number: single|str|
        # default_recycle: single|bool|None                     rest_ms
        # default_pulse_ms: single|template_ms|None             pwm1_ms
        # default_pulse_power: single|float(0,1)|None           pwm1_power
        # default_timed_enable_ms: single|template_ms|None      pwm2_ms
        # default_hold_power: single|float(0,1)|None            pwm2_power
        # pulse_with_timed_enable: single|bool|false            pwm2_enable
        # max_pulse_ms: single|ms|None
        # max_pulse_power: single|float(0,1)|1.0
        # max_hold_power: single|float(0,1)|None
        # max_hold_duration: single|secs|None
        # platform_settings: single|dict|None

        fast_config = copy(self.hw_driver_config)

        # Mode 00 - Disable
        # Mode 10 - Pulse
        # Mode 12 - Pulse + Kick
        # Mode 18 - Pulse + Hold
        if mpf_config.default_pulse_ms:
            fast_config.mode = '18'
            fast_config.param1 = Util.int_to_hex_string(mpf_config.default_pulse_ms)  # pwm1_ms
            fast_config.param2 = Util.float_to_hex(mpf_config.default_hold_power) # pwm1_power
            fast_config.param3 = Util.float_to_hex(mpf_config.default_hold_power) # pwm2_power
            fast_config.param4 = '00'  # rest_ms # TODO
            fast_config.param5 = '00'

        else:
            assert False # missed one

        # Mode 30 - Delayed Pulse
        # Mode 70 - Long Pulse
        # Mode 75 - Pulse w/ Cancel Switch
        # Mode 78 - Pulse + Hold w/ Extension

        return fast_config

    def send_config_to_driver(self):
        # TODO this sends hw_driver_config, switch version sends MPF config
        msg = (f'{self.communicator.driver_cmd}:{self.number},{self.hw_driver_config.trigger},'
               f'{self.hw_driver_config.switch_id},{self.hw_driver_config.mode},{self.hw_driver_config.param1},'
               f'{self.hw_driver_config.param2},{self.hw_driver_config.param3},{self.hw_driver_config.param4},'
               f'{self.hw_driver_config.param5}')
        self.communicator.send_with_confirmation(msg, f'{self.communicator.driver_cmd}')
        self.hw_config_good = True

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

    def get_hold_pwm_for_cmd(self, power):
        """Return a hex string for a float power setting for hold."""
        if self.platform_settings.get('hold_pwm_patter'):
            return self.platform_settings['hold_pwm_patter']

        return self.get_pwm_for_cmd(power)

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
                self.get_recycle_ms_for_cmd(self.config.default_recycle, pulse_settings.duration)
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
