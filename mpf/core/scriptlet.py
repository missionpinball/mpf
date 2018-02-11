"""Contains the parent class for Scriptlets."""
from mpf.core.delays import DelayManager
from mpf.core.logging import LogMixin


class Scriptlet(LogMixin):

    """Baseclass for scriptlet which are simple scripts in a machine."""

    def __init__(self, machine, name):
        """Initialise scriptlet."""
        super().__init__()
        self.machine = machine
        self.name = name

        self.configure_logging('Scriptlet.' + name, 'basic', 'full')
        self.delay = DelayManager(self.machine.delayRegistry)
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
