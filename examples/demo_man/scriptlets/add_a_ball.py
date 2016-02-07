"""Test scriptlet to add an additional ball into play"""

from mpf.core.scriptlet import Scriptlet


class AddABall(Scriptlet):

    def on_load(self):
        self.machine.events.add_handler('sw_buy_in', self.add_ball)

    def add_ball(self):

        if self.machine.game:
            self.machine.game.add_balls_in_play(1)
            self.machine.playfield.add_ball()
