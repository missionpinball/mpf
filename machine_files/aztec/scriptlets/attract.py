# Attract mode Scriptlet for Aztec

from mpf.system.scriptlet import Scriptlet


class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('machineflow_Attract_stop', self.stop)

    def start(self):
        self.machine.shows['semi_circle_rainbow'].play(repeat=True,
                                                        tocks_per_sec=15,
                                                        priority=1,
                                                        blend=True)
        self.machine.shows['kit'].play(repeat=True,
                                        tocks_per_sec=10,
                                        priority=1,
                                        blend=True)
        self.machine.shows['ball_lock_lane'].play(repeat=True,
                                        tocks_per_sec=5,
                                        priority=1,
                                        blend=True)
        #self.machine.shows['top_lanes'].play(repeat=True,
        #                                tocks_per_sec=1,
        #                                priority=1,
        #                                blend=True)

    def stop(self):
        self.machine.shows['semi_circle_rainbow'].stop()
        self.machine.shows['kit'].stop()
        self.machine.shows['ball_lock_lane'].stop()
        #self.machine.shows['top_lanes'].stop()

        for led in self.machine.leds:
            led.off()
