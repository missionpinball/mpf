"""Contains the parent class for hacklets."""
# hacklet.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging


class Hacklet(object):

    def __init__(self, machine, name):
        self.machine = machine
        self.name = name
        self.log = logging.getLogger('Hacklet.' + name)
        self.log.info("Loading Hacklet: %s", name)
        self.on_load()

    def on_load(self):
        """Automatically called when this hacklet loads. It's the intention
        that the hacklet writer will overwrite this method in the hacklet.
        """
        pass
