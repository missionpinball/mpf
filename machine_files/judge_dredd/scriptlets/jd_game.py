# Game mode for JD

from mpf.system.scriptlet import Scriptlet


class JDGame(Scriptlet):

    def on_load(self):
        self.machine.events.add_handler('machineflow_Game_start', self.start)
        self.machine.events.add_handler('machineflow_Game_stop', self.stop)

    def start(self):
        self.log.debug("Starting JD Game")
        self.machine.switch_controller.add_switch_handler('fireL',
                                                          self.fireL_switch,
                                                          1, 0)

    def stop(self):
        self.log.debug("Stopping JD Game")
        self.machine.switch_controller.remove_switch_handler('fireL',
                                                             self.fireL_switch,
                                                             1, 0)

    def fireL_switch(self):
        self.machine.ball_controller.add_live()
        self.machine.game.num_balls_in_play += 1
