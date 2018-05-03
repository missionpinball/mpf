"""Mypinballs hardware platform."""
import asyncio
import logging
import re

from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface

from mpf.core.platform import SegmentDisplayPlatform


class MyPinballsSegmentDisplay(SegmentDisplayPlatformInterface):

    """A physical display on the mypinballs controller."""

    def __init__(self, number, platform) -> None:
        """Initialise segment display."""
        super().__init__(number)
        self.platform = platform        # type: MyPinballsHardwarePlatform

        # clear the display
        self.set_text("", False)

    def set_text(self, text: str, flashing: bool):
        """Set digits to display."""
        if not text:
            # blank display
            cmd = b'3:' + bytes([ord(str(self.number))]) + b'\n'
        else:
            # remove any non-numbers and spaces
            text = re.sub(r'[^0-9 ]', "", text)

            # special char for spaces
            text = text.replace(" ", "?")
            # set text
            if flashing:
                cmd = b'2:'
            else:
                cmd = b'1:'
            cmd += bytes([ord(str(self.number))]) + b':' + text.encode() + b'\n'
        self.platform.send_cmd(cmd)


class MyPinballsHardwarePlatform(SegmentDisplayPlatform):

    """Hardware platform for MyPinballs 7-segment controller."""

    def __init__(self, machine):
        """Initialise mypinballs hardware."""
        super().__init__(machine)

        self._writer = None
        self._reader = None
        self.config = None
        self.log = logging.getLogger('mypinballs')

    @asyncio.coroutine
    def initialize(self):
        """Initialise hardware."""
        self.config = self.machine.config_validator.validate_config("mypinballs", self.machine.config['mypinballs'])

        # connect to serial
        connector = self.machine.clock.open_serial_connection(
            url=self.config['port'], baudrate=self.config['baud'])
        self._reader, self._writer = yield from connector

        # send a newline to end any previous command in the queue
        # this caused problems. disable it for now
        # self.send_cmd(b'\n')

    def stop(self):
        """Stop platform."""
        if self._writer:
            self._writer.close()

    def send_cmd(self, cmd: bytes):
        """Send a byte command."""
        if self.config['debug']:
            self.log.debug("Sending cmd: %s", cmd)
        self._writer.write(cmd)

    def configure_segment_display(self, number: str) -> "SegmentDisplayPlatformInterface":
        """Configure display."""
        number_int = int(number)
        if 1 > number_int > 6:
            raise AssertionError("Number {} invalid for mypinballs display. 1-6 are valid.".format(number))

        return MyPinballsSegmentDisplay(number_int, self)
