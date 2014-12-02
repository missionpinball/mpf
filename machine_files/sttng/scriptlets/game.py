# Game mode Scriptlet for Big Shot

from mpf.system.scriptlet import Scriptlet


class Game(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('machineflow_Game_start', self.start)
        self.machine.events.add_handler('machineflow_Game_stop', self.stop)
#        self.machine.events.add_handler('timer_tick', self.tick)

    def start(self):

        # turn on the GI
        for light in self.machine.lights.items_tagged('GI'):
            light.on()

    def tick(self):
        pass
#        self.machine.platform.verify_switches()

    def enable_classic_mode(self):
        pass

    def enable_modern_mode(self):
        pass

    def stop(self):
        self.machine.events.remove_handler(self.player_added)
        self.machine.events.remove_handler(self.ball_started)

    def player_added(self, **kwargs):
        pass

    def ball_started(self, **kwargs):
        self.log.debug("Game Scriplet ball_started()")

        # Need this since Big Shot's plunger lane is not a ball device,
        # so we need to automatically launch a "live" ball when the ball
        # starts
        
        if not self.machine.ball_controller.num_balls_live:
            self.machine.ball_controller.add_live()

        # Gabe put this in because we need to make sure the 8 ball lights
        # are turned off when a ball starts. They seem to have a mind of
        # their own since there's no device attached to them
