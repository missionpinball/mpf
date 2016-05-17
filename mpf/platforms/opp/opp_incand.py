import logging

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPIncandCard(object):

    def __init__(self, addr, mask, incand_dict):
        self.log = logging.getLogger('OPPIncand')
        self.addr = addr
        self.oldState = 0
        self.newState = 0
        self.mask = mask

        self.log.debug("Creating OPP Incand at hardware address: 0x%02x", addr)

        card = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                number = card + '-' + str(index)
                incand_dict[number] = OPPIncand(self, number)


class OPPIncand(object):

    def __init__(self, incand_card, number):
        self.incandCard = incand_card
        self.number = number

    def off(self):
        """Disables (turns off) this matrix light."""
        _, incand = self.number.split("-")
        curr_bit = (1 << int(incand))
        self.incandCard.newState &= ~curr_bit

    def on(self, brightness=255, fade_ms=0, start=0):
        """Enables (turns on) this driver."""
        del fade_ms
        del start
        _, incand = self.number.split("-")
        curr_bit = (1 << int(incand))
        if brightness == 0:
            self.incandCard.newState &= ~curr_bit
        else:
            self.incandCard.newState |= curr_bit
