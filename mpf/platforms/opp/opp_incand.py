"""Support for incandescent wings in OPP."""
import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade
from mpf.platforms.opp.opp_modern_lights import OPPModernLightChannel

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPIncandCard:

    """An incandescent wing card."""

    __slots__ = ["log", "addr", "chain_serial", "old_state", "new_state", "card_num", "machine", "hardware_fade_ms",
                 "mask"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, machine):
        """Initialise OPP incandescent card."""
        self.log = logging.getLogger('OPPIncand {} on {}'.format(addr, chain_serial))
        self.addr = addr
        self.chain_serial = chain_serial
        self.old_state = None
        self.new_state = 0
        self.mask = mask
        self.machine = machine
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        self.hardware_fade_ms = int(1 / machine.config['mpf']['default_light_hw_update_hz'] * 1000)

        self.log.debug("Creating OPP Incand at hardware address: 0x%02x", addr)

    def configure_software_fade_incand(self, number):
        """Configure traditional incand."""
        return OPPIncand(self, number, self.hardware_fade_ms, self.machine.clock.loop)

    def configure_modern_fade_incand(self, number, light_system):
        """Configure modern incand with fade."""
        return OPPModernLightChannel(self.chain_serial, int(self.card_num), int(number) + 0x1000, light_system)

    def is_valid_light_number(self, number):
        """Check if incand light exists in hardware."""
        return ((1 << int(number)) & self.mask) != 0


class OPPIncand(LightPlatformSoftwareFade):

    """A driver of an incandescent wing card."""

    __slots__ = ["incand_card", "index"]

    def __init__(self, incand_card, number, hardware_fade_ms, loop):
        """Initialise Incandescent wing card driver."""
        super().__init__(number, loop, hardware_fade_ms)
        self.incand_card = incand_card  # type: OPPIncandCard
        self.index = int(number)

    def set_brightness(self, brightness: float):
        """Enable (turns on) this driver.

        Args:
        ----
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
        return ((self.incand_card.chain_serial, self.incand_card.addr, self.index) <
                (other.incand_card.chain_serial, other.incand_card.addr, other.index))
