# Attract mode Scriptlet for Big Shot

from mpf.system.scriptlet import Scriptlet


class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('machineflow_Attract_stop', self.stop)

    def start(self):
        self.machine.lights['midPlastic'].on()
        self.machine.lights['ball12'].on()
        self.machine.lights['ball11'].on()
        self.machine.lights['ball9'].on()
        self.machine.lights['ball8'].on()
        self.machine.lights['ball15'].on()
        self.machine.lights['ball14'].on()
        self.machine.lights['ball10'].on()

    def stop(self):
        self.machine.lights['g_s'].off()
