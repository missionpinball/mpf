"""MPF-MC virtual segment display emulator platform."""
import re

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

        # clear the display
        self.set_text("", FlashingType.NO_FLASH)

    @classmethod
    def get_segment_display_config_section(cls):
        """Return addition config section for segment displays."""
        return "mpfmc_segment_display"

    def set_text(self, text: str, flashing: FlashingType, platform_options: dict = None):
        """Send text characters to display."""
        self.platform.send(self.number, text)


class MpfMcSegmentDisplayEmulatorPlatform(SegmentDisplayPlatform):
    """Platform for MPF-MC Segment Display Emulator (14-segment).

    NOTE: This virtual platform communicates with MPF-MC via the standard BCP connection
    used by the MC. Since the segment display emulator utilizes a custom widget for
    display, the existing widget player communication mechanism is used to communicate
    with each display. The widget name of each display is used and a widget update
    trigger is sent with the text to display. Additional display options (such as
    transitions, flash, etc.) are handled through additional parameters in the
    platform_settings dictionary.
    """

    def __init__(self, machine):
        """Initialise platform."""
        super().__init__(machine)

        self.bcp_client = None
        self.config = self.machine.config_validator.validate_config("mpfmc_segment_display_emulator",
                                                                    self.machine.config[
                                                                        'mpfmc_segment_display_emulator'])
        self._configure_device_logging_and_debug("MpfMcSegmentDisplayEmulator", self.config)

    async def initialize(self):
        """Initialise hardware."""

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

    def stop(self):
        """Stop platform."""
        pass

    def send(self, number: str, text: str):
        """Send text to the specified display widget in the MPF-MC."""
        self.machine.bcp.interface.bcp_trigger_client(self.bcp_client,
                                                      name="update_segment_display_{}".format(number),
                                                      text=text)

    async def configure_segment_display(self, name: str, platform_settings) -> "SegmentDisplayPlatformInterface":
        """Configure display."""
        return MpfMcSegmentDisplayEmulator(name,
                                           platform_settings["character_count"],
                                           self)
