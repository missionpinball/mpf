from mpf.system.platform import DriverOverlay

class Snux(DriverOverlay):
    pass

    def __init__(self, machine):
        self.machine = machine

    def driver_enable(self):
        pass

    def driver_disable(self):
        pass

    def driver_pulse(self):
        pass

    def write_hw_rule(self, *args, **kwargs):
        print "SNUX write hw rule"

    def clear_hw_rule(self):
        pass