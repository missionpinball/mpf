"""PKONE Lightshow board."""
import logging

from mpf.core.platform_batch_light_system import PlatformBatchLight


class PKONELightshowBoard:
    """PKONE Lightshow board."""

    __slots__ = ["log", "addr", "firmware_version", "hardware_rev", "rgbw_firmware", "simple_led_count", "led_groups",
                 "max_leds_per_group"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, addr, firmware_version, hardware_rev, rgbw_firmware=False):
        """Initialize PKONE Lightshow board."""
        self.log = logging.getLogger('PKONELightshowBoard {}'.format(addr))
        self.addr = addr
        self.firmware_version = firmware_version
        self.rgbw_firmware = rgbw_firmware
        self.hardware_rev = hardware_rev
        self.simple_led_count = 40  # numbers 1 - 40
        self.led_groups = 8  # numbers 1 - 8
        self.max_leds_per_group = 48 if rgbw_firmware else 64  # numbers 1 - 64 for RGB, 1 - 48 for RGBW

    def get_description_string(self) -> str:
        """Return description string."""
        if self.rgbw_firmware:
            return "PKONE Lightshow Board {} - RGBW Firmware: {}, Hardware Rev: {}, Simple LEDs: {}, " \
                   "RGBW LED Groups: {} (max {} LEDs per RGBW group)".format(self.addr,
                                                                             self.firmware_version,
                                                                             self.hardware_rev,
                                                                             self.simple_led_count,
                                                                             self.led_groups,
                                                                             self.max_leds_per_group)

        return "PKONE Lightshow Board {} - RGB Firmware: {}, Hardware Rev: {}, Simple LEDs: {}, " \
               "RGB LED Groups: {} (max {} LEDs per RGB group)".format(self.addr,
                                                                       self.firmware_version,
                                                                       self.hardware_rev,
                                                                       self.simple_led_count,
                                                                       self.led_groups,
                                                                       self.max_leds_per_group)


class PKONELightChannel(PlatformBatchLight):
    """A channel of a WS2812 LED."""

    __slots__ = ["addr", "group", "index"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, addr, group, index, light_system):
        """Initialise led channel."""
        super().__init__("{}-{}-{}".format(addr, group, index), light_system)
        self.addr = addr
        self.group = group
        self.index = index

    def get_max_fade_ms(self):
        """Return max fade (ms)."""
        return 40960

    def get_board_name(self):
        """Return OPP chain and addr."""
        return "PKONE LED {} on Group {} Board {}".format(self.index, self.group, self.addr)

    def is_successor_of(self, other):
        """Return true if the other light has the previous pixel_num and is on the same group and addr."""
        return (self.addr == other.addr and self.group == other.group and
                self.index == other.index + 1)

    def get_successor_number(self):
        """Return next index on the same group and addr."""
        return "{}-{}-{}".format(self.addr, self.group, self.index + 1)

    def __lt__(self, other):
        """Order lights by their position on the hardware."""
        return (self.addr, self.group, self.index) < (other.addr, other.group, other.index)

    def __repr__(self):
        """Return str representation."""
        return "<PKONELightChannel addr={} group={} index={}>".format(self.addr, self.group, self.index)
