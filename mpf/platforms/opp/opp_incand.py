"""Support for incandescent wings in OPP."""
import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPIncandCard:

    """An incandescent wing card."""

    __slots__ = ["log", "addr", "chain_serial", "old_state", "new_state", "mask", "card_num"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, incand_dict, machine):
        """Initialise OPP incandescent card."""
        self.log = logging.getLogger('OPPIncand')
        self.addr = addr
        self.chain_serial = chain_serial
        self.old_state = None
        self.new_state = 0
        self.mask = mask
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        hardware_fade_ms = int(1 / machine.config['mpf']['default_light_hw_update_hz'] * 1000)

        self.log.debug("Creating OPP Incand at hardware address: 0x%02x", addr)

        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                number = self.card_num + '-' + str(index)
                incand_dict[chain_serial + '-' + number] = OPPIncand(self, chain_serial + '-' + number,
                                                                     hardware_fade_ms, machine.clock.loop)


class OPPIncand(LightPlatformSoftwareFade):

    """A driver of an incandescent wing card."""

    __slots__ = ["incand_card", "index"]

    def __init__(self, incand_card, number, hardware_fade_ms, loop):
        """Initialise Incandescent wing card driver."""
        super().__init__(number, loop, hardware_fade_ms)
        self.incand_card = incand_card  # type: OPPIncandCard
        _, _, incand = self.number.split("-")
        self.index = int(incand)

    def set_brightness(self, brightness: float):
        """Enable (turns on) this driver.

        Args:
            brightness: brightness 0 (off) to 255 (on) for this incandescent light. OPP only supports on (>0) or off.
        """
        curr_bit = (1 << self.index)
        if brightness == 0:
            self.incand_card.new_state &= ~curr_bit
        else:
            self.incand_card.new_state |= curr_bit

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.incand_card.chain_serial), "0x%02x" % self.incand_card.addr)

    def is_successor_of(self, other):
        """Return true if the other light has the previous index and is on the same card."""
        return self.incand_card == other.incand_card and self.index == self.index + 1

    def get_successor_number(self):
        """Return next index on node."""
        return "{}-{}-{}".format(self.incand_card.chain_serial, self.incand_card.addr, self.index + 1)

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return (self.incand_card.chain_serial < other.incand_card.chain_serial or
                self.incand_card.addr < other.incand_card.addr or self.index < self.index)
