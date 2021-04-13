"""MPF-MC virtual segment display emulator platform."""
import re
from typing import Any, List

from mpf.core.rgb_color import RGBColor
from mpf.platforms.interfaces.segment_display_platform_interface import SegmentDisplayPlatformInterface, FlashingType
from mpf.core.platform import SegmentDisplayPlatform


class MpfMcSegmentDisplayEmulator(SegmentDisplayPlatformInterface):
    """A segment display emulator in MPF-MC (uses segment display widget)."""

    __slots__ = ["character_count", "platform", "platform_settings"]

    def __init__(self, number: any, character_count: int, platform) -> None:
        """Initialize segment display."""
        super().__init__(number)
        self.character_count = character_count
        self.platform = platform        # type: MpfMcSegmentDisplayEmulatorPlatform

    @classmethod
    def get_segment_display_config_section(cls):
        """Return addition config section for segment displays."""
        return "mpfmc_segment_display"

    def set_text(self, text: str, flashing: FlashingType, platform_options: dict = None):
        """Send text characters to display."""
        self.platform.send_text_update(self.number, text)

    def set_color(self, colors: List[RGBColor]) -> None:
        """Set the color(s) of the display."""
        self.platform.send_color_update(self.number, colors)


class MpfMcSegmentDisplayEmulatorPlatform(SegmentDisplayPlatform):
    """Platform for MPF-MC Segment Display Emulator (14-segment).

    NOTE: This virtual platform communicates with MPF-MC via the standard BCP connection
    used by the MC.
    """

    def __init__(self, machine):
        """Initialize platform."""
        super().__init__(machine)

        self.bcp_client = None
        self.config = self.machine.config_validator.validate_config("mpfmc_segment_display_emulator",
                                                                    self.machine.config[
                                                                        'mpfmc_segment_display_emulator'])
        self._configure_device_logging_and_debug("MpfMcSegmentDisplayEmulator", self.config)

    @classmethod
    def get_segment_display_config_section(cls):
        """Return addition config section for segment displays."""
        return "mpfmc_segment_displays"

    async def initialize(self):
        """Initialize hardware."""
        # The platform cannot connect to the MPF-MC at this time because the BCP connection has not yet
        # been configured. The connection cannot be verified at this point in the MPF boot process.
        # Subscribe to event so the platform is aware when all BCP clients have been connected
        self.machine.events.add_handler('bcp_clients_connected', self._bcp_clients_connected)

    def _bcp_clients_connected(self, **kwargs):
        del kwargs
        # All BCP clients are now connected. Determine which connection to use to communicate with MPF-MC
        self.bcp_client = self.machine.bcp.transport.get_named_client(self.config['bcp_connection'])
        if not self.bcp_client:
            raise AssertionError("Could not establish BCP connection to MPF-MC via using client name {}.".format(
                self.config['bcp_connection']))

        # Remove the event handler since it is only triggered once
        self.machine.events.remove_handler(self._bcp_clients_connected)

    def stop(self):
        """Stop platform."""
        pass

    def send_text_update(self, number: str, text: str):
        """Send text to the specified display widget in the MPF-MC."""
        self.machine.bcp.interface.bcp_trigger_client(self.bcp_client,
                                                      name="update_segment_display_{}_text".format(number),
                                                      text=text)

    def send_color_update(self, number: str, color: Any):
        """Send text to the specified display widget in the MPF-MC."""
        self.machine.bcp.interface.bcp_trigger_client(self.bcp_client,
                                                      name="update_segment_display_{}_color".format(number),
                                                      color=color)

    async def configure_segment_display(self, name: str, platform_settings) -> "SegmentDisplayPlatformInterface":
        """Configure display."""
        return MpfMcSegmentDisplayEmulator(name,
                                           platform_settings["character_count"],
                                           self)
