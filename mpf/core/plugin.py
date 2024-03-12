"""Contains the MPF Plugin class."""

from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util

class MpfPlugin(LogMixin):

    __slots__ = ("machine", "name")

    config_section = None

    def __init__(self, machine):
        """Initialize custom code but with custom logging formatter."""
        super().__init__()
        self.machine = machine
        self.name = type(self).__name__

        if self.config_section and self.config_section not in self.machine.config:
            self.machine.log.debug('"%s:" section not found in machine '
                    'configuration, so the %s will not be '
                    'used.', self.config_section, self.name)

    def initialize(self):
        """Called when the plugin is enabled and loaded into MPF.

        Override with plugin-specific init behavior.
        """
        pass

    @property
    def is_plugin_enabled(self):
        """If false, this plugin will not be attached to the MPF process.

        Override with class-specific logic.
        """
        if self.config_section:
            return self.config_section in self.machine.config
        return True
