"""OPP solenoid wings."""
import logging
from collections import namedtuple
from typing import Optional, Dict

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface, PulseSettings, HoldSettings

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf

SwitchRule = namedtuple("SwitchRule", ["pulse_settings", "hold_settings", "recycle", "can_cancel"])


class OPPSolenoid(DriverPlatformInterface):

    """Driver of an OPP solenoid card."""

    __slots__ = ["solCard", "log", "switch_rule", "_switches", "_config_state", "platform_settings", "switches"]

    def __init__(self, sol_card, number):
        """Initialise OPP solenoid driver."""
        super().__init__({}, number)
        self.solCard = sol_card
        self.log = sol_card.log
        self.switch_rule = None        # type: SwitchRule
        self.switches = []
        self._config_state = None
        self.platform_settings = dict()     # type: Dict

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.solCard.chain_serial), "0x%02x" % self.solCard.addr)

    def get_minimum_off_time(self, recycle):
        """Return minimum off factor.

        The hardware applies this factor to pulse_ms to prevent the coil from burning.
        """
        if not recycle:
            return 0
        elif self.platform_settings['recycle_factor']:
            if self.platform_settings['recycle_factor'] > 7:
                raise AssertionError("Maximum recycle_factor allowed is 7")
            return self.platform_settings['recycle_factor']
        else:
            # default to two times pulse_ms
            return 2

    def _kick_coil(self, sol_int, on):
        mask = 1 << sol_int
        msg = bytearray()
        msg.append(self.solCard.addr)
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
        cmd = bytes(msg)
        self.log.debug("Triggering solenoid driver: %s", "".join(" 0x%02x" % b for b in cmd))
        self.solCard.platform.send_to_processor(self.solCard.chain_serial, cmd)

    def disable(self):
        """Disable (turns off) this driver."""
        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
        self.log.debug("Disabling solenoid %s", self.number)
        self._kick_coil(sol_int, False)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable (turns on) this driver."""
        self.reconfigure_driver(pulse_settings, hold_settings, False)

        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
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
        self.log.debug("Pulsing solenoid %s", self.number)
        self._kick_coil(sol_int, True)

        # restore rule if there was one
        self.apply_switch_rule()

    def remove_switch_rule(self):
        """Remove switch rule."""
        self.switch_rule = None
        self.reconfigure_driver(
            PulseSettings(
                duration=self.config.default_pulse_ms if self.config.default_pulse_ms is not None else 10,
                power=self.config.default_pulse_power),
            HoldSettings(power=self.config.default_hold_power),
            True)

    def set_switch_rule(self, pulse_settings: PulseSettings, hold_settings: Optional[HoldSettings], recycle: bool,
                        can_cancel: bool):
        """Set and apply a switch rule."""
        new_rule = SwitchRule(pulse_settings, hold_settings, recycle, can_cancel)
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

        self._config_state = new_config_state

        # If hold is 0, set the auto clear bit
        if not hold_settings or not hold_settings.power:
            cmd = ord(OppRs232Intf.CFG_SOL_AUTO_CLR)
            hold = 0
        else:
            cmd = 0
            hold = int(hold_settings.power * 16)
            if hold >= 16:
                if self.solCard.platform.minVersion >= 0x00020000:
                    # set flag for full power
                    cmd += ord(OppRs232Intf.CFG_SOL_ON_OFF)
                    hold = 0
                else:
                    hold = 15

        minimum_off = self.get_minimum_off_time(recycle)
        _, _, solenoid = self.number.split('-')

        # Before version 0.2.0.0 set solenoid input wasn't available.
        # CFG_SOL_USE_SWITCH was used to enable/disable a solenoid.  This
        # will work as long as switches are added using _add_switch_coil_mapping
        if self.switch_rule:
            if self.solCard.platform.minVersion < 0x00020000:
                cmd += ord(OppRs232Intf.CFG_SOL_USE_SWITCH)
            elif str(((int(solenoid) & 0x0c) << 1) | (int(solenoid) & 0x03)) in\
                    [switch.split('-')[2] for switch in self.switches]:
                # If driver is using matching switch set CFG_SOL_USE_SWITCH
                # in case config happens after set switch command
                cmd += ord(OppRs232Intf.CFG_SOL_USE_SWITCH)

            if self.switch_rule.can_cancel:
                cmd += ord(OppRs232Intf.CFG_SOL_CAN_CANCEL)

        pulse_len = pulse_settings.duration

        msg = bytearray()
        msg.append(self.solCard.addr)
        msg.extend(OppRs232Intf.CFG_IND_SOL_CMD)
        msg.append(int(solenoid))
        msg.append(cmd)
        msg.append(pulse_len)
        msg.append(hold + (minimum_off << 4))
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        final_cmd = bytes(msg)

        self.log.debug("Writing individual config: %s", "".join(" 0x%02x" % b for b in final_cmd))
        self.solCard.platform.send_to_processor(self.solCard.chain_serial, final_cmd)


class OPPSolenoidCard:

    """OPP solenoid card."""

    __slots__ = ["log", "chain_serial", "addr", "mask", "platform", "state", "cardNum"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, sol_dict, platform):
        """Initialise OPP solenoid card."""
        self.log = logging.getLogger('OPPSolenoid')
        self.chain_serial = chain_serial
        self.addr = addr
        self.mask = mask
        self.platform = platform
        self.state = 0
        self.cardNum = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Solenoid at hardware address: 0x%02x", addr)

        for index in range(0, 16):
            if ((1 << index) & mask) != 0:
                number = chain_serial + '-' + self.cardNum + '-' + str(index)
                opp_sol = OPPSolenoid(self, number)
                opp_sol.config = {}
                sol_dict[number] = opp_sol
