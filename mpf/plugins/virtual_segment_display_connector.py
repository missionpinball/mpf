"""MPF plugin which connects segment displays to MPF-MC to update segment display emulator widgets."""

import logging
from typing import Any

from mpf.core.rgb_color import RGBColor
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class VirtualSegmentDisplayConnector:

    """MPF plugin which connects segment displays to MPF-MC to update segment display emulator widgets."""

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

    def set_text(self, name: str, text: str, flashing: FlashingType) -> None:
        """Set the display text to send to MPF-MC via BCP."""
        self.machine.bcp.interface.bcp_trigger_client(
            client=self.bcp_client,
            name='update_segment_display',
            segment_display_name=name,
            text=text,
            flashing=flashing)

    def set_color(self, name: str, colors: Any) -> None:
        """Set the display colors to send to MPF-MC via BCP."""
        if not isinstance(colors, list):
            colors = [colors]
        self.machine.bcp.interface.bcp_trigger_client(
            client=self.bcp_client,
            name='update_segment_display',
            segment_display_name=name,
            color=[RGBColor(color).hex for color in colors])
