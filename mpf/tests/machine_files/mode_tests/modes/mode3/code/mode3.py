from mpf.core.mode import Mode


class Mode3(Mode):
    def mode_init(self):
        self.custom_code = True

    def mode_start(self, **kwargs):
        pass

    def mode_stop(self, **kwargs):
        pass
