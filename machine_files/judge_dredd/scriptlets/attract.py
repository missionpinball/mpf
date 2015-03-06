# Attract mode Scriptlet for Judge Dredd

from mpf.system.scriptlet import Scriptlet
from mpf.system.show_controller import Show


class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('ball_ending', self.reset_display,
                                        priority=1000)

    def start(self):

        for gi in self.machine.gi:
            gi.on()

    def reset_display(self, **kwargs):
        self.machine.display.displays['Window'].slides['default'].remove_element('ball number')
        self.machine.display.displays['Window'].slides['default'].remove_element('player number')

        #self.machine.platform.verify_switches()
