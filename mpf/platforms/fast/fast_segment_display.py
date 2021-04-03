"""Segment display on the FAST platform."""
import logging

from typing import Optional
from typing import List

from mpf.core.utility_functions import Util
from mpf.core.rgb_color import RGBColor

from mpf.platforms.fast.fast_serial_communicator import FastSerialCommunicator

from mpf.platforms.interfaces.segment_display_platform_interface import ColorSegmentDisplayPlatformInterface, FlashingType

from time import sleep
class FASTSegmentDisplay(ColorSegmentDisplayPlatformInterface):

    """FAST segment display."""

    __slots__ = ["serial", "hex_id"]

    def __init__(self, index, communicator):
        """Initialise alpha numeric display."""
        super().__init__(index)
        self.serial = communicator
        self.hex_id = Util.int_to_hex_string(index * 7)

    def set_text(self, text: str, flashing: FlashingType=FlashingType.NO_FLASH) -> None:
        """Set digits to display."""
        self.serial.send(('PA:{},{}').format(
            self.hex_id, text[0:7]))

    def set_color(self, colors: RGBColor):
        """Set display color."""
        self.serial.platform.info_log("Color: {}".format(colors))
        if len(colors) == 1:
            colors = (RGBColor(colors[0]).hex + ',') * 7
        else:
            colors = ','.join([RGBColor(color).hex for color in colors])
        self.serial.send(('PC:{},{}').format(
            self.hex_id, colors))

    def _delayed_write(self, text_cmd):
        """Debugging method for reduced serial communication speed."""
        self.serial.platform.debug_log(text_cmd)
        while (len(text_cmd) > 0):
            self.serial.writer.write(text_cmd[0:1].encode())
            text_cmd = text_cmd[1:]
            sleep(0.001)
        self.serial.writer.write("\r".encode())
