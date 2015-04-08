# Attract mode Scriptlet for Demo Man

from mpf.system.scriptlet import Scriptlet

class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('machineflow_Attract_stop', self.stop)

    def start(self):

        for gi in self.machine.gi:
            gi.on()

    def stop(self):

        for light in self.machine.lights:
            light.off()
