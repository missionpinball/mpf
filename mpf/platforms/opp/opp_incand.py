"""Support for incandescent wings in OPP."""
import logging

from mpf.platforms.interfaces.gi_platform_interface import GIPlatformInterface

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPIncandCard(object):

    """An incandescent wing card."""

    def __init__(self, chain_serial, addr, mask, incand_dict):
        """Initialise OPP incandescent card."""
        self.log = logging.getLogger('OPPIncand')
        self.addr = addr
        self.chain_serial = chain_serial
        self.oldState = 0
        self.newState = 0
        self.mask = mask

        self.log.debug("Creating OPP Incand at hardware address: 0x%02x", addr)

        card = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                number = card + '-' + str(index)
                incand_dict[chain_serial + '-' + number] = OPPIncand(self, number)


class OPPIncand(GIPlatformInterface):

    """A driver of an incandescent wing card."""

    def __init__(self, incand_card, number):
        """Initialise Incandescent wing card driver."""
        self.incandCard = incand_card
        self.number = number

    def off(self):
        """Disable (turns off) this light."""
        _, incand = self.number.split("-")
        curr_bit = (1 << int(incand))
        self.incandCard.newState &= ~curr_bit

    def on(self, brightness: int=255):
        """Enable (turns on) this driver.

        Args:
            brightness: brightness 0 (off) to 255 (on) for this incandescent light. OPP only supports on (>0) or off.
        """
        _, incand = self.number.split("-")
        curr_bit = (1 << int(incand))
        if brightness == 0:
            self.incandCard.newState &= ~curr_bit
        else:
            self.incandCard.newState |= curr_bit
