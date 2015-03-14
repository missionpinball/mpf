# Attract mode Scriptlet for Judge Dredd

from mpf.system.scriptlet import Scriptlet

class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start', self.start)

    def start(self):

        for gi in self.machine.gi:
            gi.on()
