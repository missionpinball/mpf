# Game mode Scriptlet for Aztec

from mpf.system.scriptlet import Scriptlet


class Game(Scriptlet):

    def on_load(self):

        self.machine.events.add_handler('ball_started', self.ball_started)

    def ball_started(self, **kwargs):
        # Need this since the plunger lane is not a ball device, so we need to
        # automatically launch a "live" ball when the ball starts

        if not self.machine.ball_controller.num_balls_live:
            self.machine.ball_controller.add_live()