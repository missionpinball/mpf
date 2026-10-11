"""PKONE Lightshow board."""
import logging
from typing import Optional

from mpf.platforms.pkone.pkone_lights import PKONELEDChannel


# pylint: disable-msg=too-many-instance-attributes
class PKONELightshowBoard:

    """PKONE Lightshow board."""

    __slots__ = ["log", "addr", "firmware_version", "hardware_rev", "rgbw_firmware", "simple_led_count", "led_groups",
                 "max_leds_per_group", "_channel_hw_drivers", "mixed_firmware", "group_types"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, addr, firmware_version, hardware_rev, rgbw_firmware=False, mixed_firmware=False):
        """Initialize PKONE Lightshow board."""
        self.log = logging.getLogger('PKONELightshowBoard {}'.format(addr))
        self.addr = addr
        self.firmware_version = firmware_version
        self.rgbw_firmware = rgbw_firmware
        self.mixed_firmware = mixed_firmware
        self.group_types = {}
        self.hardware_rev = hardware_rev
        self.simple_led_count = 40  # numbers 1 - 40
        self.led_groups = 8  # numbers 1 - 8
        self.max_leds_per_group = 64  # numbers 1 - 64 for both RGB and RGBW
        self._channel_hw_drivers = {}

        for group in range(1, self.led_groups + 1):
            self._channel_hw_drivers[group] = {}

    def channels_for_group(self, group):
        """Return the configured wire width; never guess for a mixed board."""
        group = int(group)
        if not 1 <= group <= 8:
            raise AssertionError("PKONE LED group must be 1-8")
        if not self.mixed_firmware:
            return 4 if self.rgbw_firmware else 3
        if group not in self.group_types:
            raise AssertionError(f"Configure pkone: lightshow_groups: '{self.addr}-{group}' as rgb or rgbw")
        return self.group_types[group]

    def get_description_string(self) -> str:
        """Return description string."""
        if self.mixed_firmware:
            return (f"PKONE Lightshow Board {self.addr} - mixed RGB/RGBW firmware: "
                    f"{self.firmware_version}, Hardware Rev: {self.hardware_rev}, "
                    f"configured groups: {self.group_types}")
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

    def add_channel_hw_driver(self, group: int, channel: PKONELEDChannel):
        """Add a channel hardware driver."""
        self._channel_hw_drivers[group][channel.number] = channel

    def get_channel_hw_driver(self, group: int, number: str) -> Optional[PKONELEDChannel]:
        """Get a channel hardware driver."""
        return self._channel_hw_drivers[group].get(number, None)

    def get_all_channel_hw_drivers(self):
        """Retrieve list of all channel hardware drivers configured for use with the Lightshow board."""
        hw_drivers = []
        for group in range(1, self.led_groups + 1):
            hw_drivers.extend(list(self._channel_hw_drivers[group].values()))
        return hw_drivers
