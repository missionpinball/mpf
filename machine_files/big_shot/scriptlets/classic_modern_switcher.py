# Classic / modern switcher Scriptlet for Big Shot

from mpf.system.scriptlet import Scriptlet


class ClassicModern(Scriptlet):

    def on_load(self):
        # Register the switch handler for the classic/modern switch
        self.machine.switch_controller.add_switch_handler(
            switch_name='classic_mode', state=1, ms=0,
            callback=self.enable_classic_mode)
        self.machine.switch_controller.add_switch_handler(
            switch_name='classic_mode', state=0, ms=0,
            callback=self.enable_modern_mode)

        # Set initial mode
        if self.machine.switch_controller.is_active('classic_mode'):
            self.enable_classic_mode()
        else:
            self.enable_modern_mode()

    def enable_classic_mode(self):
        self.machine.classic_mode = True
        self.machine.events.post('enable_classic_mode')

    def enable_modern_mode(self):
        self.machine.classic_mode = False
        self.machine.events.post('enable_modern_mode')
