# Attract mode Scriptlet for Hurricane

from mpf.system.scriptlet import Scriptlet
from mpf.system.show_controller import Show


class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('machineflow_Attract_stop', self.stop)


    def start(self):
        self.machine.shows['palace_swoop'].play(repeat=True,
                                                          tocks_per_sec=20,
                                                          priority=3,
                                                          blend=True)

    def stop(self):
        self.machine.shows['palace_swoop'].stop()
