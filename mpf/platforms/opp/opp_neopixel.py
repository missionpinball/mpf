"""OPP WS2812 wing."""
import logging

from mpf.core.platform_batch_light_system import PlatformBatchLight

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPNeopixelCard:

    """OPP Neopixel/WS2812 card."""

    __slots__ = ["log", "chain_serial", "platform", "addr", "card_num", "num_pixels", "num_color_entries",
                 "color_table_dict"]

    def __init__(self, chain_serial, addr, neo_card_dict, platform):
        """Initialise OPP Neopixel/WS2812 card."""
        self.log = logging.getLogger('OPPNeopixel')
        self.chain_serial = chain_serial
        self.addr = addr
        self.platform = platform
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        self.num_pixels = 0
        self.num_color_entries = 0
        self.color_table_dict = dict()
        neo_card_dict[chain_serial + '-' + self.card_num] = self

        self.log.debug("Creating OPP Neopixel card at hardware address: 0x%02x", addr)


class OPPLightChannel(PlatformBatchLight):

    """A channel of a WS2812 LED."""

    __slots__ = ["chain_serial", "addr", "pixel_num"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, pixel_num, light_system):
        """Initialise led channel."""
        super().__init__("{}-{}-{}".format(chain_serial, addr, pixel_num), light_system)
        self.pixel_num = pixel_num
        self.addr = addr
        self.chain_serial = chain_serial

    def get_max_fade_ms(self):
        """Return largest number which fits two bytes."""
        return 65535

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP LED {} on Chain {} Board {}".format(self.pixel_num, self.chain_serial, self.addr)
