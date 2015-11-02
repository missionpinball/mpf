import unittest

from mpf.system.machine import MachineController
import logging
import time
import sys
from mock import *
from datetime import datetime, timedelta

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

    def advance_time(self, delta):
        self.testTime += delta
        time.time.return_value = self.testTime

    def advance_time_and_run(self, delta):
        self.machine_run()
        if delta > 10:
            self.advance_time(10)
            self.machine_run()
            delta -= 10
        if delta > 10:
            self.advance_time(10)
            self.machine_run()
            delta -= 10
        if delta > 10:
            self.advance_time(10)
            self.machine_run()
            delta -= 10
        if delta > 0:
            self.advance_time(delta)
            self.machine_run()

    def machine_run(self):
        self.machine.default_platform.tick()
        self.machine.timer_tick()


    def setUp(self):
        # no logging by default
        #logging.basicConfig(level=99)

        # uncomment for debug
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s : %(levelname)s : %(name)s : %(message)s')


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
        self.advance_time_and_run(10000)
        self.machine = None
        time.time = self.realTime
        self.realTime = None

