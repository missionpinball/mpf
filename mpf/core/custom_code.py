"""Contains the parent class for custom code classes."""
from mpf.core.delays import DelayManager
from mpf.core.logging import LogMixin


class CustomCode(LogMixin):

    """Baseclass for custom code in a machine."""

    __slots__ = ["machine", "name", "delay"]

    def __init__(self, machine, name):
        """initialize custom code."""
        super().__init__()
        self.machine = machine
        self.name = name

        self.configure_logging('CustomCode.' + name, 'basic', 'full')
        self.delay = DelayManager(self.machine)
        self.on_load()

    def __repr__(self):
        """Return string representation."""
        return '<Scriptlet.{}>'.format(self.name)

    def on_load(self):
        """Automatically called when this custom code class loads.

        It's the intention that the programmer will overwrite this method
        in his custom code.
        """
