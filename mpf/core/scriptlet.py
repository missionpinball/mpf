"""Contains the parent class for DEPRECATED Scriptlets.

This is deprecated and will be removed in config_version 6 with MPF 0.60.
Use custom code instead.
"""
from mpf.core.delays import DelayManager
from mpf.core.logging import LogMixin


class Scriptlet(LogMixin):

    """Baseclass for DEPRECATED scriptlets which are simple scripts in a machine.

    This is deprecated and will be removed in config_version 6 with MPF 0.60.
    Use custom code instead.
    """

    def __init__(self, machine, name):
        """Initialise scriptlet."""
        super().__init__()
        self.machine = machine
        self.name = name

        self.configure_logging('Scriptlet.' + name, 'basic', 'full')
        self.delay = DelayManager(self.machine)
        self.on_load()

    def __repr__(self):
        """Return string representation."""
        return '<Scriptlet.{}>'.format(self.name)

    def on_load(self):
        """Automatically called when this Scriptlet loads.

        It's the intention that the Scriptlet writer will overwrite this method
        in the Scriptlet.
        """
        pass
