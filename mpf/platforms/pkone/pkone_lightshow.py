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
        self.max_leds_per_group = 64  # numbers 1 - 64 for both RGB and RGBW

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
