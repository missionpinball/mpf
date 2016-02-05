import unittest

from mpf.system.config import Config

from mpf.system.machine import MachineController
from mpf.system.utility_functions import Util
import logging
import sys
from mock import *
import time
import inspect


class TestMachineController(MachineController):
    local_mpf_config_cache = {}

    def __init__(self, options, config_patches):
        self.test_config_patches = config_patches
        self.test_init_complete = False
        super().__init__(options)
        self.clock._max_fps = 0

    def _load_mpf_config(self):
        if self.options['mpfconfigfile'] in TestMachineController.local_mpf_config_cache:
            self.config = TestMachineController.local_mpf_config_cache[self.options['mpfconfigfile']]
        else:
            super()._load_mpf_config()
            TestMachineController.local_mpf_config_cache[self.options['mpfconfigfile']] = self.config

    def _load_machine_config(self):
        super()._load_machine_config()
        self.config = Util.dict_merge(self.config, self.test_config_patches,
                                      combine_lists=False)

    def _reset_complete(self):
        self.test_init_complete = True
        super()._reset_complete()


class MpfTestCase(unittest.TestCase):
    machine_config_patches = dict()
    machine_config_patches['mpf'] = dict()
    machine_config_patches['mpf']['save_machine_vars_to_disk'] = False
    machine_config_patches['mpf']['plugins'] = list()

    def getConfigFile(self):
        """Override this method in your own test class to point to the config
        file you need for your tests.

        """
        return 'null.yaml'

    def getMachinePath(self):
        """Override this method in your own test class to point to the machine
        folder you need for your tests.

        """
        return '../tests/machine_files/null/'

    def get_platform(self):
        return 'virtual'

    def get_use_bcp(self):
        return False

    def getOptions(self):
        return {
            'force_platform': self.get_platform(),
            'mpfconfigfile': "mpf/mpfconfig.yaml",
            'machine_path': self.getMachinePath(),
            'configfile': Util.string_to_list(self.getConfigFile()),
            'debug': True,
            'bcp': self.get_use_bcp(),
            'rebuild_cache': False
        }

    def set_time(self, new_time):
        self.machine.log.debug("Moving time forward %ss",
                               new_time - self.testTime)
        self.testTime = new_time
        self.machine.clock.time.return_value = self.testTime

    def advance_time(self, delta=1):
        self.testTime += delta
        self.machine.clock.time.return_value = self.testTime

    def advance_time_and_run(self, delta=1.0):
        self.machine_run()
        end_time = self.machine.clock.get_time() + delta
        while True:
            next_delay_event = self.machine.delayRegistry.get_next_event()
            next_timer = self.machine.timing.get_next_timer()
            next_switch = self.machine.switch_controller.get_next_timed_switch_event()
            next_show_step = self.machine.show_controller.get_next_show_step()

            wait_until = next_delay_event

            if not wait_until or (next_timer and wait_until > next_timer):
                wait_until = next_timer

            if not wait_until or (next_switch and wait_until > next_switch):
                wait_until = next_switch

            if not wait_until or (next_show_step and wait_until > next_show_step):
                wait_until = next_show_step

            if wait_until and self.machine.clock.get_time() < wait_until < end_time:
                self.set_time(wait_until)
                self.machine_run()
            else:
                break

        self.set_time(end_time)
        self.machine_run()

    def machine_run(self):
        self.machine.process_frame()

    def unittest_verbosity(self):
        """Return the verbosity setting of the currently running unittest
        program, or 0 if none is running.

        """
        frame = inspect.currentframe()
        while frame:
            obj = frame.f_locals.get('self')
            if isinstance(obj, unittest.TestProgram) or isinstance(obj, unittest.TextTestRunner):
                return obj.verbosity
            frame = frame.f_back
        return 0

    def setUp(self):
        # we want to reuse config_specs to speed tests up
        Config.unload_config_spec = MagicMock()

        self.test_start_time = time.time()
        if self.unittest_verbosity() > 1:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s : %(levelname)s : %(name)s : %(message)s')
        else:
            # no logging by default
            logging.basicConfig(level=99)

        # init machine
        self.machine = TestMachineController(self.getOptions(),
                                             self.machine_config_patches)

        self.realTime = self.machine.clock.time
        self.testTime = self.realTime()
        self.machine.clock.time = MagicMock(return_value=self.testTime)

        self.machine.default_platform.timer_initialize()
        self.machine.loop_start_time = self.machine.clock.get_time()

        while not self.machine.test_init_complete:
            self.advance_time_and_run(0.01)

        self.machine.ball_controller.num_balls_known = 99
        self.advance_time_and_run(300)

    def tearDown(self):
        duration = time.time() - self.test_start_time
        if duration > 1.0:
            print("Test " + str(self.__class__) + "." + str(self._testMethodName) + " took " + str(duration) + " > 1s")
        self.machine.log.debug("Test ended")
        if sys.exc_info != (None, None, None):
            # disable teardown logging after error
            logging.basicConfig(level=99)
        # fire all delays
        self.advance_time_and_run(300)
        self.machine.clock.time = self.realTime
        self.machine = None
        self.realTime = None
