"""MPF plugin which connects segment displays to MPF-MC to update segment display emulator widgets."""

from mpf.core.plugin import MpfPlugin
from mpf.core.rgb_color import RGBColor
from mpf.devices.segment_display.segment_display_text import ColoredSegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class VirtualSegmentDisplayConnector(MpfPlugin):

    """MPF plugin which connects segment displays to MPF-MC to update segment display emulator widgets."""

    __slots__ = ["bcp_client", "config"]

    config_section = 'virtual_segment_display_connector'

    def __init__(self, machine):
        """Initialize virtual segment display connector plugin."""
        super().__init__(machine)
        self.bcp_client = None

        if self.config_section in self.machine.config and not self.machine.bcp.enabled:
            self.machine.log.debug('Disabling virtual_segment_display_connector because BCP is disabled.')

    @property
    def is_plugin_enabled(self):
        return self.config_section in self.machine.config and self.machine.bcp.enabled

    def initialize(self):
        self.configure_logging(self.name)
        self.config = self.machine.config_validator.validate_config(
            "virtual_segment_display_connector", self.machine.config['virtual_segment_display_connector'])

        # All BCP clients should be connected (plugins are loaded after BCP is initialized).
        # Determine which connection to use to communicate with MPF-MC
        self.bcp_client = self.machine.bcp.transport.get_named_client(self.config['bcp_connection'])
        if not self.bcp_client:
            raise AssertionError("Could not establish BCP connection to MPF-MC via using client name {}.".format(
                self.config['bcp_connection']))

        # loop over all configured segment displays adding the connector to each one
        if 'segment_displays' in self.config:
            for display in self.config['segment_displays']:
                display.add_virtual_connector(self)

    # pylint: disable=too-many-arguments
    def set_text(self, name: str, text: ColoredSegmentDisplayText, flashing: FlashingType, flash_mask: str) -> None:
        """Set the display text to send to MPF-MC via BCP."""
        colors = text.get_colors()
        self.machine.bcp.interface.bcp_trigger_client(
            client=self.bcp_client,
            name='update_segment_display',
            segment_display_name=name,
            text=text.convert_to_str(),
            flashing=str(flashing.value),
            flash_mask=flash_mask,
            colors=[RGBColor(color).hex for color in colors] if colors else None)
