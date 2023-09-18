"""OPP input card."""
import logging

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPInputCard:

    """OPP input card."""

    __slots__ = ["log", "chain_serial", "addr", "is_matrix", "old_state", "mask", "card_num"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, inp_dict, inp_addr_dict, platform):
        """initialize OPP input card."""
        self.log = logging.getLogger('OPPInputCard {} on {}'.format(addr, chain_serial))
        self.chain_serial = chain_serial
        self.addr = addr
        self.is_matrix = False
        self.old_state = 0
        self.mask = mask
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Input at hardware address: 0x%02x", addr)

        inp_addr_dict[chain_serial + '-' + str(addr)] = self
        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                inp_dict[self.chain_serial + "-" + self.card_num + '-' + str(index)] =\
                    OPPSwitch(self, self.chain_serial + "-" + self.card_num + '-' + str(index), platform)


class OPPMatrixCard:

    """OPP matrix input card."""

    __slots__ = ["log", "chain_serial", "addr", "mask", "is_matrix", "old_state", "card_num"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, inp_dict, inp_addr_dict, platform):
        """initialize OPP matrix input card."""
        self.log = logging.getLogger('OPPMatrixCard {} on {}'.format(addr, chain_serial))
        self.chain_serial = chain_serial
        self.addr = addr
        self.mask = 0xFFFFFFFFFFFFFFFF << 32  # create fake mask
        self.is_matrix = True
        self.old_state = [0, 0]
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Matrix Input at hardware address: 0x%02x", addr)

        inp_addr_dict[chain_serial + '-' + str(addr)] = self

        # Matrix inputs are inputs 32 - 95 (OPP only supports 8x8 input switch matrices)
        for index in range(32, 96):
            inp_dict[self.chain_serial + "-" + self.card_num + '-' + str(index)] =\
                OPPSwitch(self, self.chain_serial + "-" + self.card_num + '-' + str(index), platform)


class OPPSwitch(SwitchPlatformInterface):

    """An OPP input on an OPP input card."""

    __slots__ = ["card"]

    def __init__(self, card, number, platform):
        """initialize input."""
        super().__init__({}, number, platform)
        self.card = card

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.card.chain_serial), "0x%02x" % self.card.addr)
