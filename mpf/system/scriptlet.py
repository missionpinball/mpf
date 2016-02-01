"""Contains the parent class for Scriptlets."""

import logging


class Scriptlet(object):

    def __init__(self, machine, name):
        self.machine = machine
        self.name = name
        self.log = logging.getLogger('Scriptlet.' + name)
        self.log.debug("Loading Scriptlet: %s", name)
        self.on_load()

    def __repr__(self):
        return '<Scriptlet.{}>'.format(self.name)

    def on_load(self):
        """Automatically called when this Scriptlet loads. It's the intention
        that the Scriptlet writer will overwrite this method in the Scriptlet.
        """
        pass
