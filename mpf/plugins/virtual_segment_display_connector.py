"""MPF plugin which connects segment displays to MPF-MC to update segment display emulator widgets."""

import logging

from mpf.core.rgb_color import RGBColor
from mpf.devices.segment_display.segment_display_text import ColoredSegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class VirtualSegmentDisplayConnector:

    """MPF plugin which connects segment displays to MPF-MC to update segment display emulator widgets."""

    __slots__ = ["log", "machine", "bcp_client", "config"]

    def __init__(self, machine):
        """Initialize virtual segment display connector plugin."""
        self.log = logging.getLogger('virtual_segment_display_connector')
        self.machine = machine      # type: MachineController
        self.bcp_client = None

        if 'virtual_segment_display_connector' not in machine.config:
            self.log.debug('"virtual_segment_display_connector:" section not found in machine '
                           'configuration, so the Virtual Segment Display Connector plugin '
                           'will not be used.')
            return

        if not self.machine.bcp.enabled:
            self.log.debug('Disabling virtual_segment_display_connector because BCP is disabled.')
            return

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
