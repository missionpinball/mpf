"""Contains the parent class for Scriptlets."""
import logging
from mpf.core.delays import DelayManager


class Scriptlet(object):

    """Baseclass for scriptlet which are simple scripts in a machine."""

    def __init__(self, machine, name):
        """Initialise scriptlet."""
        self.machine = machine
        self.name = name
        self.log = logging.getLogger('Scriptlet.' + name)
        self.log.debug("Loading Scriptlet: %s", name)
        self.delay = DelayManager(self.machine.delayRegistry)
        self.on_load()

    def __repr__(self):
        """Return string representation."""
        return '<Scriptlet.{}>'.format(self.name)

    def on_load(self):
        """Automatically called when this Scriptlet loads.

        It's the intention that the Scriptlet writer will overwrite this method in the Scriptlet.
        """
        pass
