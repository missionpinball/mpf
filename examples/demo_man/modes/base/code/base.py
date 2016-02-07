from mpf.core.mode import Mode


class Base(Mode):
    def mode_init(self):
        """Sample custom code that will run for this mode when MPF boots
        """
        pass

    def mode_start(self, **kwargs):
        """Sample custom code that will run for this mode when it starts.
        """
        pass

    def mode_stop(self, **kwargs):
        """Sample custom code that will run for this mode when it stops.
        """
        pass
