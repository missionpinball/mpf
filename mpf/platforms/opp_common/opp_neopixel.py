import logging

from mpf.platforms.opp_common.opp_rs232_intf import OppRs232Intf


class OPPNeopixelCard(object):
    def __init__(self, addr, neo_card_dict, platform):
        self.log = logging.getLogger('OPPNeopixel')
        self.addr = addr
        self.platform = platform
        self.card = str(addr - ord(OppRs232Intf.CARD_ID_GEN2_CARD))
        self.numPixels = 0
        self.numColorEntries = 0
        self.colorTableDict = dict()
        neo_card_dict[self.card] = self

        self.log.debug("Creating OPP Neopixel card at hardware address: 0x%02x", addr)

    def add_neopixel(self, number, neo_dict):
        if number > self.numPixels:
            self.numPixels = number + 1
        pixel_number = self.card + '-' + str(number)
        pixel = OPPNeopixel(pixel_number, self)
        neo_dict[pixel_number] = pixel
        return pixel


class OPPNeopixel(object):

    def __init__(self, number, neo_card):
        self.log = logging.getLogger('OPPNeopixel')
        self.number = number
        self.current_color = '000000'
        self.neoCard = neo_card
        _, index = number.split('-')
        self.index_char = chr(int(index))

        self.log.debug("Creating OPP Neopixel: %s", number)

    def color(self, color):
        """Instantly sets this LED to the color passed.

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
                self.neoCard.platform.opp_connection.send(cmd)
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
            self.neoCard.platform.opp_connection.send(cmd)
