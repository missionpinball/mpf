# Attract mode Scriptlet for STTNG

from mpf.system.scriptlet import Scriptlet
from mpf.system.show_controller import Playlist


class Attract(Scriptlet):

    def on_load(self):
        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('machineflow_Attract_stop', self.stop)
        
    def start(self):
#        self.machine.lights['lt_jackpot'].off()

#        for gi in self.machine.gi:
#            print("&&&&&& ", gi.name)
#            gi.off()

#        self.machine.lights['lt_jackpot'].on()

        for gi in self.machine.gi:
            gi.on()
        
#        print "&&&&&&&&&&&&&&&&&&&&&&&"
        
    def stop(self):
        pass


