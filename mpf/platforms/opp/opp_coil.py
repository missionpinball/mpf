"""OPP solenoid wings."""
import logging
from collections import namedtuple

from typing import Optional, Dict

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.platforms.opp.opp import OppHardwarePlatform

SwitchRule = namedtuple("SwitchRule", ["pulse_settings", "hold_settings", "recycle", "can_cancel", "delay_ms"])


class OPPSolenoid(DriverPlatformInterface):

    """Driver of an OPP solenoid card."""

    __slots__ = ["sol_card", "log", "switch_rule", "_switches", "_config_state", "platform_settings", "switches"]

    def __init__(self, sol_card, number):
        """Initialize OPP solenoid driver."""
        super().__init__({}, number)
        self.sol_card = sol_card        # type: OPPSolenoidCard
        self.log = sol_card.log
        self.switch_rule = None         # type: SwitchRule
        self.switches = []
        self._config_state = None
        self.platform_settings = dict()     # type: Dict

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.sol_card.chain_serial), "0x%02x" % self.sol_card.addr)

    def get_minimum_off_time(self, recycle):
        """Return minimum off factor.

        The hardware applies this factor to pulse_ms to prevent the coil from burning.
        """
        if not recycle:
            return 0
        if self.platform_settings['recycle_factor']:
            if self.platform_settings['recycle_factor'] > 7:
                raise AssertionError("Maximum recycle_factor allowed is 7")
            return self.platform_settings['recycle_factor']

        # default to two times pulse_ms
        return 2

    def _kick_coil(self, sol_int, on):
        mask = 1 << sol_int
        msg = bytearray()
        msg.append(self.sol_card.addr)
        msg.extend(OppRs232Intf.KICK_SOL_CMD)
        if on:
            msg.append((mask >> 8) & 0xff)
            msg.append(mask & 0xff)
        else:
            msg.append(0)
            msg.append(0)
        msg.append((mask >> 8) & 0xff)
        msg.append(mask & 0xff)
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        cmd = bytes(msg)
        if self.sol_card.platform.debug:
            self.log.debug("Triggering solenoid driver: %s", "".join(" 0x%02x" % b for b in cmd))
        self.sol_card.platform.send_to_processor(self.sol_card.chain_serial, cmd)

    def disable(self):
        """Disable (turns off) this driver."""
        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
        if self.sol_card.platform.debug:
            self.log.debug("Disabling solenoid %s", self.number)
        self._kick_coil(sol_int, False)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turns on) this driver."""
        self.reconfigure_driver(pulse_settings, hold_settings, False)

        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
        if self.sol_card.platform.debug:
            self.log.debug("Enabling solenoid %s", self.number)
        self._kick_coil(sol_int, True)

        # restore rule if there was one
        self.apply_switch_rule()

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse this driver."""
        # reconfigure driver
        self.reconfigure_driver(pulse_settings, None, False)

        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
        if self.sol_card.platform.debug:
            self.log.debug("Pulsing solenoid %s", self.number)
        self._kick_coil(sol_int, True)

        # restore rule if there was one
        self.apply_switch_rule()

    def timed_enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Pulse and enable the coil for an explicit duration."""
        raise NotImplementedError

    def remove_switch_rule(self):
        """Remove switch rule."""
        self.switch_rule = None
        self.reconfigure_driver(
            PulseSettings(
                duration=self.config.default_pulse_ms if self.config.default_pulse_ms is not None else 10,
                power=self.config.default_pulse_power),
            HoldSettings(power=self.config.default_hold_power),
            True)

    # pylint: disable-msg=too-many-arguments
    def set_switch_rule(self, pulse_settings: PulseSettings, hold_settings: Optional[HoldSettings], recycle: bool,
                        can_cancel: bool, delay_ms: int):
        """Set and apply a switch rule."""
        new_rule = SwitchRule(pulse_settings, hold_settings, recycle, can_cancel, delay_ms)
        if self.switch_rule and self.switch_rule != new_rule:
            raise AssertionError("Cannot set two rule with different driver settings in opp. Old: {} New: {}".format(
                self.switch_rule, new_rule))
        self.switch_rule = new_rule
        self.apply_switch_rule()

    def apply_switch_rule(self):
        """(Re-)Apply a configured switch rule if there is one."""
        if self.switch_rule:
            self.reconfigure_driver(self.switch_rule.pulse_settings, self.switch_rule.hold_settings,
                                    self.switch_rule.recycle)

    def reconfigure_driver(self, pulse_settings: PulseSettings, hold_settings: Optional[HoldSettings],
                           recycle: bool = False):
        """Reconfigure a driver."""
        new_config_state = (pulse_settings, hold_settings, recycle, bool(self.switch_rule))

        # if config would not change do nothing
        if new_config_state == self._config_state:
            return

        if self.sol_card.platform.min_version[self.sol_card.chain_serial] >= 0x02030005:
            if self._config_state is None:
                self.reconfigure_pulse_pwm(pulse_settings)
            else:
                if self._config_state[0].power != pulse_settings.power:
                    self.reconfigure_pulse_pwm(pulse_settings)

        self._config_state = new_config_state

        # If hold is 0, set the auto clear bit
        if not hold_settings or not hold_settings.power:
            cmd = ord(OppRs232Intf.CFG_SOL_AUTO_CLR)
            hold = 0
        else:
            cmd = 0
            hold = int(hold_settings.power * 16)
            if hold >= 16:
                if self.sol_card.platform.min_version[self.sol_card.chain_serial] >= 0x00020000:
                    # set flag for full power
                    cmd += ord(OppRs232Intf.CFG_SOL_ON_OFF)
                    hold = 0
                else:
                    hold = 15
            if self.switch_rule and self.switch_rule.delay_ms:
                raise AssertionError("Cannot use hold and delayed pulses in OPP.")

        minimum_off = self.get_minimum_off_time(recycle)
        _, _, solenoid = self.number.split('-')

        # Before version 0.2.0.0 set solenoid input wasn't available.
        # CFG_SOL_USE_SWITCH was used to enable/disable a solenoid.  This
        # will work as long as switches are added using _add_switch_coil_mapping
        if self.switch_rule:
            if self.sol_card.platform.min_version[self.sol_card.chain_serial] < 0x00020000 or \
               str(((int(solenoid) & 0x0c) << 1) | (int(solenoid) & 0x03)) in \
                    [switch.split('-')[2] for switch in self.switches]:
                # Either old firmware or
                # ff driver is using matching switch set CFG_SOL_USE_SWITCH
                # in case config happens after set switch command
                cmd += ord(OppRs232Intf.CFG_SOL_USE_SWITCH)

            if self.switch_rule.can_cancel:
                cmd += ord(OppRs232Intf.CFG_SOL_CAN_CANCEL)

            if self.switch_rule.delay_ms:
                cmd += ord(OppRs232Intf.CFG_SOL_DLY_KICK)

        pulse_len = pulse_settings.duration

        msg = bytearray()
        msg.append(self.sol_card.addr)
        msg.extend(OppRs232Intf.CFG_IND_SOL_CMD)
        msg.append(int(solenoid))
        msg.append(cmd)
        msg.append(pulse_len)
        if self.switch_rule and self.switch_rule.delay_ms:
            msg.append(int(self.switch_rule.delay_ms / 2))
        else:
            msg.append(hold + (minimum_off << 4))
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        final_cmd = bytes(msg)

        if self.sol_card.platform.debug:
            self.log.debug("Writing individual config: %s on %s", "".join(" 0x%02x" % b for b in final_cmd),
                           self.sol_card.chain_serial)
        self.sol_card.platform.send_to_processor(self.sol_card.chain_serial, final_cmd)

    def reconfigure_pulse_pwm(self, pulse_settings: PulseSettings):
        """Send a new configuration for pulse PWM on this coil."""
        pwm_val = int((pulse_settings.power * 32) - 1)
        if pwm_val < 0:
            pwm_val = 0

        _, _, solenoid = self.number.split('-')

        msg = bytearray()
        msg.append(self.sol_card.addr)
        msg.extend(OppRs232Intf.CFG_SOL_KICK_PWM)
        msg.append(pwm_val)
        msg.append(int(solenoid))
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        final_cmd = bytes(msg)

        if self.sol_card.platform.debug:
            self.log.debug("Writing pulse power config: %s on %s", "".join(" 0x%02x" % b for b in final_cmd),
                           self.sol_card.chain_serial)
        self.sol_card.platform.send_to_processor(self.sol_card.chain_serial, final_cmd)


class OPPSolenoidCard:

    """OPP solenoid card."""

    __slots__ = ["log", "chain_serial", "addr", "mask", "platform", "state", "card_num"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, sol_dict, platform):
        """Initialize OPP solenoid card."""
        self.log = logging.getLogger('OPPSolenoid {} on {}'.format(addr, chain_serial))
        self.chain_serial = chain_serial
        self.addr = addr
        self.mask = mask
        self.platform = platform    # type: OppHardwarePlatform
        self.state = 0
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Solenoid at hardware address: 0x%02x", addr)

        for index in range(0, 16):
            if ((1 << index) & mask) != 0:
                number = chain_serial + '-' + self.card_num + '-' + str(index)
                opp_sol = OPPSolenoid(self, number)
                opp_sol.config = {}
                sol_dict[number] = opp_sol
