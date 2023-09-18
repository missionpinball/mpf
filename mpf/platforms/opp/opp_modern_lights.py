"""OPP WS2812 wing."""
import logging

from mpf.core.platform_batch_light_system import PlatformBatchLight

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPNeopixelCard:

    """OPP Neopixel/WS281x card."""

    __slots__ = ["log", "chain_serial", "platform", "addr", "card_num"]

    def __init__(self, chain_serial, addr, platform):
        """initialize OPP Neopixel/WS2812 card."""
        self.log = logging.getLogger('OPPNeopixel {} on {}'.format(addr, chain_serial))
        self.chain_serial = chain_serial
        self.addr = addr
        self.platform = platform
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Neopixel card at hardware address: 0x%02x", addr)

    @staticmethod
    def is_valid_light_number(number):
        """Check if neopixel number is possible in hardware."""
        return 0 <= int(number) < 0x1000


class OPPModernMatrixLightsCard:

    """OPP Matrix Lights Card with firmware >= 2.1.0."""

    __slots__ = ["log", "chain_serial", "platform", "addr", "card_num"]

    def __init__(self, chain_serial, addr, platform):
        """initialize OPP Incand card."""
        self.log = logging.getLogger('OPPMatrixLights {} on {}'.format(addr, chain_serial))
        self.chain_serial = chain_serial
        self.addr = addr
        self.platform = platform
        self.card_num = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))

        self.log.debug("Creating OPP Matrix Lights card at hardware address: 0x%02x", addr)

    @staticmethod
    def is_valid_light_number(number):
        """Check if matrix light exists in hardware."""
        return 0 <= int(number) < 64


class OPPModernLightChannel(PlatformBatchLight):

    """A channel of a WS2812 LED."""

    __slots__ = ["chain_serial", "addr", "pixel_num"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, pixel_num, light_system):
        """initialize led channel."""
        super().__init__("{}-{}-{}".format(chain_serial, addr, pixel_num), light_system)
        self.pixel_num = pixel_num
        self.addr = addr
        self.chain_serial = chain_serial

    def get_max_fade_ms(self):
        """Return largest number which fits two bytes."""
        return 65535

    def get_type_string(self):
        """Return string for the type."""
        if self.pixel_num < 0x1000:
            return "LED"

        if self.pixel_num < 0x2000:
            return "Incandescent Lamp"

        return "Matrix Lamp"

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP Light {} on Chain {} Board {} Type {}".format(
            self.pixel_num, self.chain_serial, self.addr, self.get_type_string())

    def is_successor_of(self, other):
        """Return true if the other light has the previous pixel_num and is on the same chain and addr."""
        return (self.chain_serial == other.chain_serial and self.addr == other.addr and
                self.pixel_num == other.pixel_num + 1)

    def get_successor_number(self):
        """Return nex pixel_num on the same chain and addr."""
        return "{}-{}-{}".format(self.chain_serial, self.addr, self.pixel_num + 1)

    def __lt__(self, other):
        """Order lights by their position on the hardware."""
        return (self.chain_serial, self.addr, self.pixel_num) < (other.chain_serial, other.addr, other.pixel_num)

    def __repr__(self):
        """Return str representation."""
        return "<OPPLightChannel type={} chain={} addr={} pixel={}>".format(
            self.get_type_string(), self.chain_serial, self.addr, self.pixel_num)
