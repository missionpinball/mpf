# ball search
import logging
import mpf.events
import mpf.tasks


class BallSearch(object):
    """
    """

    def __init__(self, machine):
        self.log = logging.getLogger('BallSearch')
        self.machine = machine
        self.active = False

        # Setup ball search coils
        self.ball_search_coils = []
        for coil in self.machine.coils.items_tagged('ballSearch'):
            self.ball_search_coils.append(coil)
        self.log.debug("Found %s ball search coils",
                         len(self.ball_search_coils))

        # Register for ball search-related events
        self.machine.events.add_handler("ball_search_begin_phase1", self.start)
        self.machine.events.add_handler("ball_search_begin_phase2", self.start)
        self.machine.events.add_handler("ball_search_end", self.end)

    def start(self):
        """Begin the ball search process"""
        self.log.debug("Starting the ball search")

        self.active = True
        self.task = mpf.tasks.Task.Create(self.tick)

    def end(self):
        self.log.debug("Stopping the ball search")
        self.active = False

    def tick(self):
        """ Method that runs as a task """
        while self.active:
            for coil in self.ball_search_coils:
                self.pop_coil(coil)
                yield mpf.timing.Timing.secs(self.machine.config['BallSearch']\
                    ['Secs between ball search coils'])
            yield mpf.timing.Timing.secs(self.machine.config['BallSearch']\
                    ['Secs between ball search rounds'])
        # todo do we have to deal with switches that might be hit due to these
        # coils firing?
        # todo should the above code also look for self.active?

    def pop_coil(self, coil):
        """actviates the 'coil' based on it's default pulse time.
        Holds a coil open for the hold time in sec
        """
        print "popping coil", coil
        '''
        if coil.patter_on:
            coil.patter(on_time=coil.patter_on,
                        off_time=coil.patter_off,
                        original_on_time=coil.default_pulse_time,
                        now=True)
            self.log.debug("Ball Search is holding coil %s for %ss",
                             coil.name, coil.search_hold_time)
            # set a delay to turn off the coil if it's a hold coil
            self.delay(name="Ball_Search_Release", delay=coil.search_hold_time,
                       callback=self.machine.proc.driver_disable,
                       param=coil.number)
            # todo change above to platform
        elif coil.default_pulse_time:
            # if it's not a hold coil, just pulse it with the default
            coil.pulse()
            self.log.debug("Ball Search is pulsing coil %s", coil.name)
        '''
