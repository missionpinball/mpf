import logging
from collections import namedtuple

from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade, LightPlatformDirectFade

MYPY = False
if MYPY:  # pragma: no cover
    from mpf.platforms.pkone.pkone import PKONEHardwarePlatform  # pylint: disable-msg=cyclic-import,unused-import

PKONESimpleLEDNumber = namedtuple("PKONESimpleLEDNumber", ["board_address_id", "led_number"])


class PKONESimpleLED(LightPlatformSoftwareFade):
    """A simple led (single emitter/color) on a PKONE Extension board. Simple leds are either on or off."""

    __slots__ = ["log", "number", "send", "platform"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, number: PKONESimpleLEDNumber, sender, platform: "PKONEHardwarePlatform") -> None:
        """Initialise light."""
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

    def set_fade(self, start_brightness, start_time, target_brightness, target_time):
        """Perform a fade to a brightness. PKONE Simple LEDs do not support fading."""
        raise AssertionError("Fading/brightness is not supported with Simple LEDs on PKONE Lightshow board.")

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
        return (self.number.board_address_id, self.number.led_number) < (
            other.number.board_address_id, other.number.led_number)


class PKONEDirectLEDChannel(LightPlatformDirectFade):
    """Represents a single RGB LED channel connected to a PKONE hardware platform Lightshow board."""

    __slots__ = ["led", "channel"]

    def __init__(self, led: any, channel) -> None:
        """Initialise LED."""
        super().__init__("{}-{}".format(led.number, channel))
        self.led = led
        self.channel = int(channel)

    def get_max_fade_ms(self) -> int:
        """Return max fade time."""
        return 40960

    def set_brightness_and_fade(self, brightness: float, fade_ms: int) -> None:
        """Set the light to the specified brightness.

        Args:
        ----
            brightness: float of the brightness
            fade_ms: ms to fade the light

        Does not return anything.
        """
        raise NotImplementedError

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
