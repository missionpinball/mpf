"""Mypinballs hardware platform."""
import asyncio

from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface

from mpf.core.platform import SegmentDisplayPlatform


class MyPinballsSegmentDisplay(SegmentDisplayPlatformInterface):

    """A physical display on the mypinballs controller."""

    def __init__(self, number, platform) -> None:
        """Initialise segment display."""
        super().__init__(number)
        self.platform = platform        # type: MyPinballsHardwarePlatform

    def set_text(self, text: str, flashing: bool):
        """Set digits to display."""
        if not text:
            # blank display
            cmd = b'3:' + bytes([ord(str(self.number))]) + b'\n'
        else:
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
        super().__init__(machine)

        self._writer = None
        self._reader = None
        self.config = None

    @asyncio.coroutine
    def initialize(self):
        """Initialise hardware."""
        self.config = self.machine.config_validator.validate_config("mypinballs", self.machine.config['mypinballs'])

        # connect to serial
        connector = self.machine.clock.open_serial_connection(
            url=self.config['port'], baudrate=self.config['baud'])
        self._reader, self._writer = yield from connector

        # reset all displays to empty
        self.send_cmd(b'9\n')

    def stop(self):
        """Stop platform."""
        if self._writer:
            self._writer.close()

    def send_cmd(self, cmd: bytes):
        """Send a byte command."""
        self._writer.write(cmd)

    def configure_segment_display(self, number: str) -> "SegmentDisplayPlatformInterface":
        """Configure display."""
        number_int = int(number)
        if 1 > number_int > 6:
            raise AssertionError("Number {} invalid for mypinballs display. 1-6 are valid.".format(number))

        return MyPinballsSegmentDisplay(number_int, self)