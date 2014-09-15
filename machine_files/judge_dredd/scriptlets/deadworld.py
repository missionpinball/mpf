"""Template file you can customize to build your own machine-specific Scriptlets.
"""

from mpf.system.scriptlet import Scriptlet


class Deadworld(Scriptlet):

    def on_load(self):
        self.machine.events.add_handler('machineflow_Game_start', self.start)
        self.machine.events.add_handler('machineflow_Game_stop', self.stop)
        self.machine.events.add_handler('ball_ending', self.stop_globe)

    def start(self):
        self.log.debug("Starting Deadworld")
        self.machine.events.add_handler('shot_LeftRamp', self.start_globe)

    def stop(self):
        self.log.debug("Stopping Deadworld")
        self.machine.events.remove_handler(self.start_globe)
        self.stop_globe()

    def start_globe(self):
        self.log.debug("Starting Deadworld motor")
        self.machine.coils.globeMotor.enable()

    def stop_globe(self, **kwargs):
        self.log.debug("Stopping Deadworld motor")
        self.machine.coils.globeMotor.disable()
