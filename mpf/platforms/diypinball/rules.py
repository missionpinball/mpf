class PulseOnHitRule(object):
    def __init__(self, coil):
        self.coil = coil

    def process_event(self, event):
        if event.data[0] == 1:
            self.coil.pulse(None)


class PulseOnHitAndReleaseRule(object):
    def __init__(self, coil):
        self.coil = coil

    def process_event(self, event):
        if event.data[0] == 1:
            self.coil.pulse(None)


class PulseOnHitAndEnableAndReleaseRule(object):
    def __init__(self, coil):
        self.coil = coil
        self.state = 0

    def process_event(self, event):
        if event.data[0] == 1:
            self.coil.enable(None)
        else:
            self.coil.disable(None)
