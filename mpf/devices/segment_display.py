"""Physical segment displays."""
from mpf.core.system_wide_device import SystemWideDevice


class SegmentDisplay(SystemWideDevice):

    """A phyiscal segment display in a pinball machine."""

    config_section = 'segment_displays'
    collection = 'segment_displays'
    class_label = 'segment_display'

    def _initialize(self):
        """Initialise display."""
        # load platform
        self.platform = self.machine.get_platform_sections('segment_displays', self.config['platform'])

        # configure hardware
        self.hw_display = self.platform.configure_segment_display(self.config['number'])

    def set_text(self, text):
        """Set text to the display."""
        # TODO: replace variables
        # TODO: register watches on variables
        # TODO: update on variable changes
        self.hw_display.set_text(text)
