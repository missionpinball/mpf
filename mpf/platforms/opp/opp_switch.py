"""OPP input card."""
import logging

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPInputCard(object):

    """OPP input card."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, inp_dict, inp_addr_dict):
        """Initialise OPP input card."""
        self.log = logging.getLogger('OPPInputCard')
        self.chain_serial = chain_serial
        self.addr = addr
        self.oldState = 0
        self.mask = mask
        self.cardNum = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Input at hardware address: 0x%02x", addr)

        inp_addr_dict[chain_serial + '-' + str(addr)] = self
        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                inp_dict[self.chain_serial + "-" + self.cardNum + '-' + str(index)] =\
                    OPPSwitch(self, self.chain_serial + "-" + self.cardNum + '-' + str(index))


class OPPSwitch(SwitchPlatformInterface):

    """An OPP input on an OPP input card."""

    def __init__(self, card, number):
        """Initialise input."""
        super().__init__({}, number)
        self.card = card
