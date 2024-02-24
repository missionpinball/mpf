"""PKONE Lights."""
import logging
from collections import namedtuple

from mpf.core.platform import LightConfig
from mpf.core.platform_batch_light_system import PlatformBatchLight, PlatformBatchLightSystem
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade

MYPY = False
if MYPY:  # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform  # pylint: disable-msg=cyclic-import,unused-import

PKONESimpleLEDNumber = namedtuple("PKONESimpleLEDNumber", ["board_address_id", "led_number"])


class PKONESimpleLED(LightPlatformSoftwareFade):

    """A simple led (single emitter/color) on a PKONE Extension board. Simple leds are either on or off."""

    __slots__ = ["log", "number", "send", "platform"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, number: PKONESimpleLEDNumber, sender, platform: "PKONEHardwarePlatform") -> None:
        """initialize light."""
        super().__init__(number, platform.machine.clock.loop, 0)
        self.log = logging.getLogger('PKONESimpleLED')
        self.send = sender
        self.platform = platform

    def set_brightness(self, brightness: float) -> None:
        """Turn on or off this Simple LED.

        Args:
        ----
            brightness: brightness 0 (off) to 255 (on) for this Simple LED. PKONE Simple LEDs only
            support on (>0) or off.
        """
        # send the new simple LED state command (on or off)
        cmd = "PLS{}{:02d}{}".format(self.number.board_address_id,
                                     self.number.led_number,
                                     1 if brightness > 0 else 0)
        self.log.debug("Sending Simple LED Control command: %s", cmd)
        self.send(cmd)

    def get_board_name(self):
        """Return PKONE Lightshow addr."""
        if self.number.board_address_id not in self.platform.pkone_extensions.keys():
            return "PKONE Unknown Board"
        return "PKONE Lightshow Board {}".format(self.number.board_address_id)

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        raise AssertionError("Not possible using Simple LEDs on PKONE Lightshow board.")

    def get_successor_number(self):
        """Return next number."""
        raise AssertionError("Not possible using Simple LEDs on PKONE Lightshow board.")

    def __lt__(self, other):
        """Order lights by board and led number."""
        return (self.number.board_address_id, self.number.led_number) < (
            other.number.board_address_id, other.number.led_number)


class PKONELEDChannel(PlatformBatchLight):

    """Represents a single LED channel connected to a PKONE hardware platform Lightshow board."""

    __slots__ = ["board_address_id", "group", "index", "config", "_hardware_aligned"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, board_address_id, group, index,
                 config: LightConfig, light_system: PlatformBatchLightSystem) -> None:
        """initialize LED."""
        super().__init__("{}-{}-{}".format(board_address_id, group, index), light_system)
        self.board_address_id = int(board_address_id)
        self.group = int(group)
        self.index = int(index)
        self.config = config
        self._hardware_aligned = False

    def set_hardware_aligned(self, hardware_aligned: bool = True):
        """Set whether or not this channel is aligned to hardware boundaries."""
        self._hardware_aligned = hardware_aligned

    def get_max_fade_ms(self) -> int:
        """Return max fade time."""
        return 40960 if self._hardware_aligned else 0

    def get_board_name(self):
        """Return the board of this light."""
        return "PKONE LED Channel {} on Lightshow Board (Address ID {}, Group {}, Light: {}, " \
               "Hardware Aligned: {})".format(self.index,
                                              self.board_address_id,
                                              self.group,
                                              self.config.name,
                                              "Yes" if self._hardware_aligned else "No")

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        return self.board_address_id == other.board_address_id and self.group == other.group and \
            self.index == other.index + 1

    def get_successor_number(self):
        """Return next number."""
        return "{}-{}-{}".format(self.board_address_id, self.group, self.index + 1)

    def get_predecessor_number(self):
        """Return previous number."""
        if self.index > 0:
            return "{}-{}-{}".format(self.board_address_id, self.group, self.index - 1)
        return None

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return (self.board_address_id, self.group, self.index) < (other.board_address_id, other.group, other.index)

    def __repr__(self):
        """Return str representation."""
        return "<PKONELEDChannel board_address_id={} group={} index={}>".format(
            self.board_address_id, self.group, self.index)
