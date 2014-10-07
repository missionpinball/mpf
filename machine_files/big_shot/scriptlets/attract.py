# Attract mode Scriptlet for Big Shot

from mpf.system.scriptlet import Scriptlet
from mpf.system.show_controller import Playlist


class Attract(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Attract_start',
                                        self.start)
        self.machine.events.add_handler('machineflow_Attract_stop',
                                        self.stop)

    def start(self):

        for light in self.machine.lights.items_tagged('GI'):
            light.on()

        # In Big Shot, the ball sitting in the plunger lane does not sit on a
        # switch, so if the machine starts with the ball in the plunger lane,
        # we need to trick the ball controller into thinking there's a ball
        if self.machine.ball_controller.num_balls_known == 0:
            self.machine.ball_controller._num_balls_live = 1
            self.machine.ball_controller.num_balls_known = 1
            self.machine.ball_controller._num_balls_desired_live = 1

        # register for classic / modern notification
        self.machine.events.add_handler('enable_classic_mode',
                                        self.enable_classic_mode)
        self.machine.events.add_handler('enable_modern_mode',
                                        self.enable_modern_mode)

        # set initial classic / modern mode
        if self.machine.classic_mode:
            self.enable_classic_mode()
        else:
            self.enable_modern_mode()

        # Setup and start the modern shows. These play at all times. In classic
        # mode, the modern shows are still 'playing' under the boring classic
        # lights which are just off.

        self.modern_playlist = Playlist(self.machine)
        self.modern_playlist.add_show(step_num=1,
                               show=self.machine.shows['playfield_rack_snake'],
                               tocks_per_sec=10,
                               num_repeats=2,
                               repeat=True)
        self.modern_playlist.add_show(step_num=2,
                               show=self.machine.shows['playfield_rack_sweep'],
                               tocks_per_sec=10,
                               num_repeats=2,
                               repeat=True)
        self.modern_playlist.step_settings(step=1,
                        trigger_show=self.machine.shows['playfield_rack_snake'])
        self.modern_playlist.step_settings(step=2,
                        trigger_show=self.machine.shows['playfield_rack_sweep'])

        self.machine.shows['top_lanes_sweep'].play(
            repeat=True, tocks_per_sec=5)
        self.machine.shows['pop_8_alternate'].play(
            repeat=True, tocks_per_sec=5)
        self.machine.shows['mid_lights_bounce'].play(
            repeat=True, tocks_per_sec=5)
        self.modern_playlist.start()

        self.machine.events.add_handler('reload_and_play_show',
                                        self.reload_and_play_show)

    def enable_classic_mode(self):
        self.machine.shows['classic_overlay'].play(
            repeat=False, hold=True, tocks_per_sec=1, priority=1000)

    def enable_modern_mode(self):
        self.machine.shows['classic_overlay'].stop(hold=False, reset=True)

    def play_modern_shows(self):
        if not self.playlist:
            self.create_playlist()

    def stop(self):
        self.machine.shows['top_lanes_sweep'].stop()
        self.machine.shows['pop_8_alternate'].stop()
        self.machine.shows['mid_lights_bounce'].stop()
        self.modern_playlist.stop()
        self.machine.shows['classic_overlay'].stop()

        self.machine.events.remove_handler(self.enable_classic_mode)
        self.machine.events.remove_handler(self.enable_modern_mode)
        self.machine.events.remove_handler(self.reload_and_play_show)

    def reload_and_play_show(self, **kwargs):

        show_name = 'test_show'
        tocks_per_sec = 30

        self.machine.shows[show_name].reload()

        # Now play it
        self.machine.shows[show_name].play(repeat=False,
                                           tocks_per_sec=tocks_per_sec)









