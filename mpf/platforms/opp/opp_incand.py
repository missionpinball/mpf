"""Support for incandescent wings in OPP."""
import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPIncandCard(object):

    """An incandescent wing card."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, addr, mask, incand_dict, machine):
        """Initialise OPP incandescent card."""
        self.log = logging.getLogger('OPPIncand')
        self.addr = addr
        self.chain_serial = chain_serial
        self.oldState = 0
        self.newState = 0
        self.mask = mask
        self.cardNum = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        hardware_fade_ms = int(1 / machine.config['mpf']['default_light_hw_update_hz'] * 1000)

        self.log.debug("Creating OPP Incand at hardware address: 0x%02x", addr)

        for index in range(0, 32):
            if ((1 << index) & mask) != 0:
                number = self.cardNum + '-' + str(index)
                incand_dict[chain_serial + '-' + number] = OPPIncand(self, chain_serial + '-' + number,
                                                                     hardware_fade_ms, machine.clock.loop)


class OPPIncand(LightPlatformSoftwareFade):

    """A driver of an incandescent wing card."""

    def __init__(self, incand_card, number, hardware_fade_ms, loop):
        """Initialise Incandescent wing card driver."""
        super().__init__(number, loop, hardware_fade_ms)
        self.incandCard = incand_card

    def set_brightness(self, brightness: float):
        """Enable (turns on) this driver.

        Args:
            brightness: brightness 0 (off) to 255 (on) for this incandescent light. OPP only supports on (>0) or off.
        """
        _, _, incand = self.number.split("-")
        curr_bit = (1 << int(incand))
        if brightness == 0:
            self.incandCard.newState &= ~curr_bit
        else:
            self.incandCard.newState |= curr_bit

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.incandCard.chain_serial), "0x%02x" % self.incandCard.addr)
