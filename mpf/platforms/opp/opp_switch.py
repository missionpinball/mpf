"""OPP input card."""
import logging

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPInputCard:

    """OPP input card."""

    __slots__ = ["log", "chain_serial", "addr", "isMatrix", "oldState", "mask", "cardNum"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, inp_dict, inp_addr_dict):
        """Initialise OPP input card."""
        self.log = logging.getLogger('OPPInputCard')
        self.chain_serial = chain_serial
        self.addr = addr
        self.isMatrix = False
        self.oldState = 0
        self.mask = mask
        self.cardNum = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Input at hardware address: 0x%02x", addr)

        inp_addr_dict[chain_serial + '-' + str(addr)] = self
        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                inp_dict[self.chain_serial + "-" + self.cardNum + '-' + str(index)] =\
                    OPPSwitch(self, self.chain_serial + "-" + self.cardNum + '-' + str(index))


class OPPMatrixCard:

    """OPP matrix input card."""

    __slots__ = ["log", "chain_serial", "addr", "mask", "isMatrix", "oldState", "cardNum"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, inp_dict, inp_addr_dict):
        """Initialise OPP matrix input card."""
        self.log = logging.getLogger('OPPMatrixCard')
        self.chain_serial = chain_serial
        self.addr = addr
        self.mask = 0xFFFFFFFFFFFFFFFF << 32  # create fake mask
        self.isMatrix = True
        self.oldState = [0, 0]
        self.cardNum = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Matrix Input at hardware address: 0x%02x", addr)

        inp_addr_dict[chain_serial + '-' + str(addr)] = self

        # Matrix inputs are inputs 32 - 95 (OPP only supports 8x8 input switch matrices)
        for index in range(32, 96):
            inp_dict[self.chain_serial + "-" + self.cardNum + '-' + str(index)] =\
                OPPSwitch(self, self.chain_serial + "-" + self.cardNum + '-' + str(index))


class OPPSwitch(SwitchPlatformInterface):

    """An OPP input on an OPP input card."""

    __slots__ = ["card"]

    def __init__(self, card, number):
        """Initialise input."""
        super().__init__({}, number)
        self.card = card

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.card.chain_serial), "0x%02x" % self.card.addr)
