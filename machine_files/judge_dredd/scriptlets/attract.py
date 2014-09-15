# Attract mode Scriptlet for Judge Dredd

from mpf.system.scriptlet import Scriptlet
from mpf.system.show_controller import Show


class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('machineflow_Attract_stop', self.stop)

    def start(self):

        self.machine.shows['drop_target_sweep'].play(repeat=True,
                                                          tocks_per_sec=5,
                                                          priority=3,
                                                          blend=True)
        self.machine.shows['chain_sweep'].play(repeat=True,
                                                    tocks_per_sec=8,
                                                    priority=3,
                                                    blend=True)
        self.machine.shows['flipper_area_flash'].play(repeat=True,
                                                           tocks_per_sec=4,
                                                           priority=3,
                                                           blend=True)
        self.machine.shows['lock_sweep'].play(repeat=True,
                                                   tocks_per_sec=5,
                                                   priority=3,
                                                   blend=True)
        self.machine.shows['crime_sweep'].play(repeat=True,
                                                    tocks_per_sec=5,
                                                    priority=3,
                                                    blend=True)
        self.machine.shows['perp_sweep'].play(repeat=True,
                                                   tocks_per_sec=4,
                                                   priority=3,
                                                   blend=True)
        self.machine.shows['random_blinking'].play(repeat=True,
                                                        tocks_per_sec=4,
                                                        priority=3,
                                                        blend=True)

        for gi in self.machine.gi:
            gi.on()

    def stop(self):
        self.machine.shows['drop_target_sweep'].stop()
        self.machine.shows['chain_sweep'].stop()
        self.machine.shows['flipper_area_flash'].stop()
        self.machine.shows['lock_sweep'].stop()
        self.machine.shows['crime_sweep'].stop()
        self.machine.shows['perp_sweep'].stop()
        self.machine.shows['random_blinking'].stop()
