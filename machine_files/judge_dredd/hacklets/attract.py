# Attract mode hacklet for Judge Dredd

from mpf.system.light_controller import LightShow


class Attract(object):

    def __init__(self, machine):

        self.machine = machine
        self.machine.events.add_handler('machineflow_Attract_start', self.start)
        self.machine.events.add_handler('machineflow_Attract_stop', self.stop)

    def start(self):
        self.ls_judge_sweep = LightShow(self.machine,
            'machine_files/judge_dredd/light_shows/drop_target_sweep.yaml')
        self.ls_judge_sweep.play(repeat=True, tocks_per_sec=5, priority=3,
                                 blend=True)

        self.ls_chain_sweep = LightShow(self.machine,
            'machine_files/judge_dredd/light_shows/chain_sweep.yaml')
        self.ls_chain_sweep.play(repeat=True, tocks_per_sec=8, priority=3,
                                 blend=True)

        self.flipper_area_flash = LightShow(self.machine,
            'machine_files/judge_dredd/light_shows/flipper_area_flash.yaml')
        self.flipper_area_flash.play(repeat=True, tocks_per_sec=4, priority=3,
                                     blend=True)

        self.lock_sweep = LightShow(self.machine,
            'machine_files/judge_dredd/light_shows/lock_sweep.yaml')
        self.lock_sweep.play(repeat=True, tocks_per_sec=5, priority=3,
                             blend=True)

        self.crime_sweep = LightShow(self.machine,
            'machine_files/judge_dredd/light_shows/crime_sweep.yaml')
        self.crime_sweep.play(repeat=True, tocks_per_sec=5, priority=3,
                             blend=True)

        self.perp_sweep = LightShow(self.machine,
            'machine_files/judge_dredd/light_shows/perp_sweep.yaml')
        self.perp_sweep.play(repeat=True, tocks_per_sec=4, priority=3,
                             blend=True)

        self.random_blinking = LightShow(self.machine,
            'machine_files/judge_dredd/light_shows/random_blinking.yaml')
        self.random_blinking.play(repeat=True, tocks_per_sec=4, priority=3,
                             blend=True)

    def stop(self):
        self.ls_judge_sweep.stop()
        self.ls_chain_sweep.stop()
        self.flipper_area_flash.stop()
        self.lock_sweep.stop()
        self.crime_sweep.stop()
        self.perp_sweep.stop()
        self.random_blinking.stop()
