"""OPP solenoid wings."""
import logging

from mpf.platforms.interfaces.driver_platform_interface import DriverPlatformInterface

from mpf.core.utility_functions import Util
from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPSolenoid(DriverPlatformInterface):

    """Driver of an OPP solenoid card."""

    def __init__(self, sol_card, number):
        """Initialise OPP solenoid driver."""
        super().__init__({}, number)
        self.solCard = sol_card
        self.log = sol_card.log
        self.can_be_pulsed = False
        self.use_switch = False

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.solCard.chain_serial), "0x%02x" % self.solCard.addr)

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

    def disable(self, coil):
        """Disable (turns off) this driver."""
        del coil

        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
        self.log.debug("Disabling solenoid %s", self.number)
        self._kick_coil(sol_int, False)

    def enable(self, coil):
        """Enable (turns on) this driver."""
        if self.solCard.platform.get_hold_value(coil.hw_driver) == 0:
            raise AssertionError("Coil {} cannot be enabled. You need to specify either allow_enable or hold_power".
                                 format(self.number))

        if self.can_be_pulsed:
            self.solCard.platform.reconfigure_driver(coil, True)

        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
        self.log.debug("Enabling solenoid %s", self.number)
        self._kick_coil(sol_int, True)

    def pulse(self, coil, milliseconds):
        """Pulse this driver."""
        if not self.can_be_pulsed:
            if self.use_switch:
                raise AssertionError("Cannot currently pulse driver {} because hw_rule needs hold_power".
                                     format(self.number))
            self.solCard.platform.reconfigure_driver(coil, False)

        if milliseconds and milliseconds != self.config['pulse_ms']:
            raise AssertionError("OPP platform doesn't allow changing pulse width using pulse call. "
                                 "Tried {}, used {}".format(milliseconds, self.config['pulse_ms']))

        _, _, solenoid = self.number.split("-")
        sol_int = int(solenoid)
        self.log.debug("Pulsing solenoid %s", self.number)
        self._kick_coil(sol_int, True)

        hex_ms_string = self.config['pulse_ms']
        return Util.hex_string_to_int(hex_ms_string)


class OPPSolenoidCard(object):

    """OPP solenoid card."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, sol_dict, platform):
        """Initialise OPP solennoid card."""
        self.log = logging.getLogger('OPPSolenoid')
        self.chain_serial = chain_serial
        self.addr = addr
        self.mask = mask
        self.platform = platform
        self.state = 0

        self.log.debug("Creating OPP Solenoid at hardware address: 0x%02x", addr)

        card = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        for index in range(0, 16):
            if ((1 << index) & mask) != 0:
                number = chain_serial + '-' + card + '-' + str(index)
                opp_sol = OPPSolenoid(self, number)
                opp_sol.config = self._create_driver_settings(platform.machine)
                sol_dict[number] = opp_sol

    @classmethod
    def _create_driver_settings(cls, machine):
        return_dict = dict()
        pulse_ms = machine.config['mpf']['default_pulse_ms']
        return_dict['pulse_ms'] = str(pulse_ms)
        return_dict['hold_power'] = '0'
        return return_dict
