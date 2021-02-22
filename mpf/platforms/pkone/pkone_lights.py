import logging
from collections import namedtuple

from mpf.core.platform_batch_light_system import PlatformBatchLight
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade, LightPlatformDirectFade, \
    LightPlatformInterface

MYPY = False
if MYPY:  # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform  # pylint: disable-msg=cyclic-import,unused-import

PKONESimpleLEDNumber = namedtuple("PKONESimpleLEDNumber", ["board_address_id", "led_number"])


class PKONESimpleLED(LightPlatformSoftwareFade):
    """A simple led (single emitter/color) on a PKONE Extension board."""

    __slots__ = ["log", "number", "send", "platform"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, number: PKONESimpleLEDNumber, sender, machine, platform: "PKONEHardwarePlatform") -> None:
        """Initialise light."""
        super().__init__(number, machine.clock.loop, 0)
        self.log = logging.getLogger('PKONESimpleLED')
        self.send = sender
        self.platform = platform

    def set_brightness(self, brightness: float):
        """Set simple LED brightness."""
        on_off = 1 if brightness > 0 else 0
        cmd = "PLS{}{:02d}{}{:02d}E".format(self.number.board_address_id, self.number.led_number, on_off,
                                            int(brightness * 99))
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
        """Order lights by string."""
        return self.number < other.number


class PKONEDirectLEDChannel(LightPlatformInterface):
    """Represents a single RGB LED channel connected to a PKONE hardware platform Lightshow board."""

    __slots__ = ["led", "channel"]

    def __init__(self, led: any, channel) -> None:
        """Initialise LED."""
        super().__init__("{}-{}".format(led.number, channel))
        self.led = led
        self.channel = int(channel)
        self._current_fade = (0, -1, 0, -1)
        self._last_brightness = None

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Set brightness via callback."""
        self.led.dirty = True
        self._current_fade = (start_brightness, start_time, target_brightness, target_time)
        self._last_brightness = None

    def get_fade_and_brightness(self, current_time):
        """Return fade + brightness and mark as clean if this is it."""
        if self._last_brightness:
            return self._last_brightness, 0, True
        max_fade_ms = self.led.hardware_fade_ms
        start_brightness, start_time, target_brightness, target_time = self._current_fade
        fade_ms = int((target_time - current_time) * 1000.0)
        if fade_ms > max_fade_ms > 0:
            fade_ms = max_fade_ms
            ratio = ((current_time + (fade_ms / 1000.0) - start_time) /
                     (target_time - start_time))
            brightness = start_brightness + (target_brightness - start_brightness) * ratio
            done = False
        else:
            if fade_ms < 0:
                fade_ms = 0
            brightness = target_brightness
            self._last_brightness = brightness
            done = True

        return brightness, fade_ms, done

    def get_board_name(self):
        """Return the board of this light."""
        return "FAST LED CPU"

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        return self.led.number_int * 3 + self.channel == other.led.number_int * 3 + other.channel + 1

    def get_successor_number(self):
        """Return next number."""
        if self.channel == 2:
            return "{}-0".format(self.led.number_int + 1)

        return "{}-{}".format(self.led.number_int, self.channel + 1)

    def __lt__(self, other):
        """Order lights by their order on the hardware."""
        return (self.led.number_int, self.channel) < (other.led.number_int, other.channel)
