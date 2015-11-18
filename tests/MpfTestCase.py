import unittest

from mpf.system.machine import MachineController
import logging
import time
import sys
from mock import *
from datetime import datetime, timedelta
import inspect

# TODO: mock BCP and prevent logs


class MpfTestCase(unittest.TestCase):

    def getOptions(self):
        return {
            'physical_hw': False,
            'mpfconfigfile': "mpf/mpfconfig.yaml",
            'machinepath': self.getMachinePath(),
            'configfile': self.getConfigFile(),
            'debug': True
               }

    def set_time(self, new_time):
        self.testTime = new_time
        time.time.return_value = self.testTime

    def advance_time(self, delta):
        self.testTime += delta
        time.time.return_value = self.testTime

    def advance_time_and_run(self, delta):
        end_time = time.time() + delta
        self.machine_run()
        while True:
            next_event = self.machine.delay.get_next_event()
            next_timer = self.machine.timing.get_next_timer()

            wait_until = next_event
            if wait_until and next_timer and wait_until > next_timer:
                wait_until = next_timer

            if wait_until and wait_until <= end_time:
                self.set_time(wait_until)
                self.machine_run()
            else:
                break

        self.set_time(end_time)
        self.machine_run()

    def machine_run(self):
        self.machine.default_platform.tick()
        self.machine.timer_tick()

    def unittest_verbosity(self):
        """Return the verbosity setting of the currently running unittest
        program, or 0 if none is running.

        """
        frame = inspect.currentframe()
        while frame:
            self = frame.f_locals.get('self')
            if isinstance(self, unittest.TestProgram):
                return self.verbosity
            frame = frame.f_back
        return 0

    def setUp(self):
        if self.unittest_verbosity() > 1:
                logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s : %(levelname)s : %(name)s : %(message)s')
        else:
                # no logging by default
                logging.basicConfig(level=99)

        self.realTime = time.time
        self.testTime = self.realTime()
        time.time = MagicMock(return_value=self.testTime)

        # init machine
        self.machine = MachineController(self.getOptions())

        self.machine.default_platform.timer_initialize()
        self.machine.loop_start_time = time.time()

        self.machine.ball_controller.num_balls_known = 99
        self.advance_time_and_run(300)


    def tearDown(self):
        if sys.exc_info != (None, None, None):
            # disable teardown logging after error
            logging.basicConfig(level=99)
        # fire all delays
        self.advance_time_and_run(300)
        self.machine = None
        time.time = self.realTime
        self.realTime = None

