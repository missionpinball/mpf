"""OPP WS2812 wing."""
import logging

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf


class OPPNeopixelCard(object):

    """OPP Neopixel/WS2812 card."""

    def __init__(self, chain_serial, addr, neo_card_dict, platform):
        """Initialise OPP Neopixel/WS2812 card."""
        self.log = logging.getLogger('OPPNeopixel')
        self.chain_serial = chain_serial
        self.addr = addr
        self.platform = platform
        self.cardNum = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        self.numPixels = 0
        self.numColorEntries = 0
        self.colorTableDict = dict()
        neo_card_dict[chain_serial + '-' + self.cardNum] = self

        self.log.debug("Creating OPP Neopixel card at hardware address: 0x%02x", addr)

    def add_channel(self, pixel_number, neo_dict, index):
        """Add a channel."""
        hardware_fade_ms = int(1 / self.platform.machine.config['mpf']['default_light_hw_update_hz'] * 1000)
        if self.cardNum + '-' + str(pixel_number) not in neo_dict:
            self.add_neopixel(pixel_number, neo_dict)

        return OPPLightChannel(self.chain_serial, neo_dict[self.cardNum + '-' + str(pixel_number)], int(index),
                               hardware_fade_ms, self.platform.machine.clock.loop)

    def add_neopixel(self, number, neo_dict):
        """Add a LED channel."""
        if number > self.numPixels:
            self.numPixels = number + 1
        pixel_number = self.cardNum + '-' + str(number)
        pixel = OPPNeopixel(pixel_number, self)
        neo_dict[pixel_number] = pixel
        return pixel


class OPPLightChannel(LightPlatformSoftwareFade):

    """A channel of a WS2812 LED."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, chain_serial, led, index, hardware_fade_ms, loop):
        """Initialise led channel."""
        super().__init__("{}-{}-{}".format(chain_serial, led.number, index), loop, hardware_fade_ms)
        self.led = led
        self.index = index

    def set_brightness(self, brightness: float):
        """Set brightness."""
        self.led.set_channel(self.index, int(brightness * 255))

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "OPP {} Board {}".format(str(self.led.neoCard.chain_serial), "0x%02x" % self.led.neoCard.addr)


class OPPNeopixel:

    """One WS2812 LED."""

    def __init__(self, number, neo_card):
        """Initialise LED."""
        self.log = logging.getLogger('OPPNeopixel')
        self.number = number
        self.current_color = '000000'
        self.neoCard = neo_card
        _, index = number.split('-')
        self.index_char = chr(int(index))
        self._color = [0, 0, 0]
        self.dirty = False

        self.log.debug("Creating OPP Neopixel: %s", number)

    def set_channel(self, index, brightness):
        """Set one channel."""
        self._color[index] = brightness
        self.dirty = True

    def update_color(self):
        """Update neopixel."""
        self.color(self._color)
        self.dirty = False

    def color(self, color):
        """Instantly set this LED to the color passed.

        Args:
            color: a 3-item list of integers representing R, G, and B values,
            0-255 each.
        """
        new_color = "{0}{1}{2}".format(hex(int(color[0]))[2:].zfill(2),
                                       hex(int(color[1]))[2:].zfill(2),
                                       hex(int(color[2]))[2:].zfill(2))
        error = False

        # Check if this color exists in the color table
        if new_color not in self.neoCard.colorTableDict:
            # Check if there are available spaces in the table
            if self.neoCard.numColorEntries < 32:
                # Send the command to add color table entry
                self.neoCard.colorTableDict[new_color] = self.neoCard.numColorEntries + OppRs232Intf.NEO_CMD_ON
                msg = bytearray()
                msg.append(self.neoCard.addr)
                msg.extend(OppRs232Intf.CHNG_NEO_COLOR_TBL)
                msg.append(self.neoCard.numColorEntries)
                msg.append(int(new_color[2:4], 16))
                msg.append(int(new_color[:2], 16))
                msg.append(int(new_color[-2:], 16))
                msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
                cmd = bytes(msg)
                self.log.debug("Add Neo color table entry: %s", "".join(" 0x%02x" % b for b in cmd))
                self.neoCard.platform.send_to_processor(self.neoCard.chain_serial, cmd)
                self.neoCard.numColorEntries += 1
            else:
                error = True
                self.log.warning("Not enough Neo color table entries. OPP only supports 32.")

        # Send msg to set the neopixel
        if not error:
            msg = bytearray()
            msg.append(self.neoCard.addr)
            msg.extend(OppRs232Intf.SET_IND_NEO_CMD)
            msg.append(ord(self.index_char))
            msg.append(self.neoCard.colorTableDict[new_color])
            msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
            cmd = bytes(msg)
            self.log.debug("Set Neopixel color: %s", "".join(" 0x%02x" % b for b in cmd))
            self.neoCard.platform.send_to_processor(self.neoCard.chain_serial, cmd)
