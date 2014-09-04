# Coil tests for Big Shot


class CoilTests(object):

    def __init__(self, machine):

        self.machine = machine
        self.holding_coil = None
        self.machine.events.add_handler('coil_test', self.coil_test)
        self.machine.events.add_handler('advance_reel_test', self.advance_reel)
        self.machine.events.add_handler('hold_coil', self.hold_coil)

    def coil_test(self, coil_name, pulse_change=0):
        if pulse_change:
            self.machine.coils[coil_name].pulse_ms += pulse_change
            self.log.debug("+-----------------------------------------------+")
            self.log.debug("|                                               |")
            self.log.debug("|   Coil: %s   New pulse time: %s           |",
                           self.machine.coils[coil_name].name,
                           self.machine.coils[coil_name].pulse_ms)
            self.log.debug("|                                               |")
            self.log.debug("+-----------------------------------------------+")
        else:
            self.log.debug("+-----------------------------------------------+")
            self.log.debug("|                                               |")
            self.log.debug("|   Coil: %s   PULSING: %s                |",
                           self.machine.coils[coil_name].name,
                           self.machine.coils[coil_name].pulse_ms)
            self.log.debug("|                                               |")
            self.log.debug("+-----------------------------------------------+")
            self.machine.coils[coil_name].pulse()

    def advance_reel(self, reel_name, direction=1):
        self.machine.score_reels[reel_name].advance(int(direction))

    def hold_coil(self, coil_name, hold_time):
        self.delay.add('kill_the_coil', hold_time, self.hold_coil_kill)
        self.holding_coil = coil_name
        self.machine.coils[coil_name].enable()

    def hold_coil_kill(self):
        print "+-----------------------------------------------+"
        print "coil: ", self.holding_coil
        print "pulse time (ms):", (time.time() - self.machine.coils[
                                  self.holding_coil].time_last_changed) * 1000
        print "+-----------------------------------------------+"
        self.machine.coils[self.holding_coil].disable()

    def test(self, param=None):
        print "test"
        print "param", param
