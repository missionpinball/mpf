import logging

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPInputCard(object):
    def __init__(self, addr, mask, inp_dict, inp_addr_dict):
        self.log = logging.getLogger('OPPInputCard')
        self.addr = addr
        self.oldState = 0
        self.mask = mask
        self.cardNum = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Input at hardware address: 0x%02x", addr)

        inp_addr_dict[addr] = self
        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                inp_dict[self.cardNum + '-' + str(index)] = OPPSwitch(self, self.cardNum + '-' + str(index))


class OPPSwitch(SwitchPlatformInterface):
    def __init__(self, card, number):
        self.number = number
        self.card = card
        self.config = {}
