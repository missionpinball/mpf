import copy
import inspect
import logging
import os
import sys
import time
import unittest

from mock import *

import ruamel.yaml as yaml

import mpf.core
import mpf.core.config_validator
from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util
from mpf.file_interfaces.yaml_interface import YamlInterface

YamlInterface.cache = True


class TestMachineController(MachineController):
    local_mpf_config_cache = {}

    def __init__(self, mpf_path, machine_path, options, config_patches,
                 enable_plugins=False):
        self.test_config_patches = config_patches
        self.test_init_complete = False
        self._enable_plugins = enable_plugins
        super().__init__(mpf_path, machine_path, options)
        self.clock._max_fps = 0

    def _reset_complete(self):
        self.test_init_complete = True
        super()._reset_complete()

    def _register_plugin_config_players(self):
        if self._enable_plugins:
            super()._register_plugin_config_players()

    def _load_config(self):
        super()._load_config()
        self.config = Util.dict_merge(self.config, self.test_config_patches)


class MpfTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.machine_config_patches = dict()
        self.machine_config_patches['mpf'] = dict()
        self.machine_config_patches['mpf']['save_machine_vars_to_disk'] = False
        self.machine_config_patches['mpf']['plugins'] = list()
        self.machine_config_patches['bcp'] = []
        self.expected_duration = 0.5
        self.min_frame_time = 1/30  # test with default Hz

    def getConfigFile(self):
        """Override this method in your own test class to point to the config
        file you need for your tests.

        """
        return 'null.yaml'

    def getMachinePath(self):
        """Override this method in your own test class to point to the machine
        folder you need for your tests.

        Path is related to the MPF package root

        """
        return 'tests/machine_files/null/'

    def getAbsoluteMachinePath(self):
        # creates an absolute path based on machine_path
        return os.path.abspath(os.path.join(
            mpf.core.__path__[0], os.pardir, self.getMachinePath()))

    def get_abs_path(self, path):
        return os.path.join(os.path.abspath(os.curdir), path)

    def post_event(self, event_name):
        self.machine.events.post(event_name)
        self.machine_run()

    def set_num_balls_known(self, balls):
        # in case the test does not have any ball devices
        self.machine.ball_controller.num_balls_known = balls

    def get_platform(self):
        return 'virtual'

    def get_use_bcp(self):
        return False

    def get_enable_plugins(self):
        return False

    def getOptions(self):

        mpfconfig = os.path.abspath(os.path.join(
            mpf.core.__path__[0], os.pardir, 'mpfconfig.yaml'))

        return {
            'force_platform': self.get_platform(),
            'mpfconfigfile': mpfconfig,
            'configfile': Util.string_to_list(self.getConfigFile()),
            'debug': True,
            'bcp': self.get_use_bcp(),
            'no_load_cache': False,
            'create_config_cache': True,
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

        # todo do we want to add clock scheduled events here?

        while True:
            next_delay_event = self.machine.delayRegistry.get_next_event()
            next_switch = \
                self.machine.switch_controller.get_next_timed_switch_event()
            next_show_step = self.machine.show_controller.get_next_show_step()

            wait_until = next_delay_event

            if not wait_until or (next_switch and wait_until > next_switch):
                wait_until = next_switch

            if not wait_until or (next_show_step and wait_until > next_show_step):
                wait_until = next_show_step

            if wait_until and wait_until - self.machine.clock.get_time() < self.min_frame_time:
                wait_until = self.machine.clock.get_time() + self.min_frame_time

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
            if isinstance(obj, unittest.TestProgram) or isinstance(obj,
                                                                   unittest.TextTestRunner):
                return obj.verbosity
            frame = frame.f_back
        return 0

    def save_and_prepare_sys_path(self):
        # save path
        self._sys_path = copy.deepcopy(sys.path)

        mpf_path = os.path.abspath(os.path.join(mpf.core.__path__[0], os.pardir))
        if mpf_path in sys.path:
            sys.path.remove(mpf_path)

    def restore_sys_path(self):
        # restore sys path
        sys.path = self._sys_path

    def setUp(self):
        # we want to reuse config_specs to speed tests up
        mpf.core.config_validator.ConfigValidator.unload_config_spec = (
            MagicMock())

        self._events = {}

        # print(threading.active_count())

        self.test_start_time = time.time()
        if self.unittest_verbosity() > 1:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s : %(levelname)s : %('
                                       'name)s : %(message)s')
        else:
            # no logging by default
            logging.basicConfig(level=99)

        self.save_and_prepare_sys_path()

        # init machine
        machine_path = self.getAbsoluteMachinePath()

        try:
            self.machine = TestMachineController(
                os.path.abspath(os.path.join(
                    mpf.core.__path__[0], os.pardir)), machine_path,
                self.getOptions(), self.machine_config_patches,
                self.get_enable_plugins())
            self.realTime = self.machine.clock.time
            self.testTime = self.realTime()
            self.machine.clock.time = MagicMock(return_value=self.testTime)

            self.machine.default_platform.timer_initialize()
            self.machine.loop_start_time = self.machine.clock.get_time()

            start = time.time()
            while not self.machine.test_init_complete and time.time() < start + 20:
                self.advance_time_and_run(0.01)

            self.advance_time_and_run(1)

        except Exception as e:
            # todo temp until I can figure out how to stop the asset loader
            # thread automatically.
            try:
                self.machine.stop()
            except AttributeError:
                pass
            raise e

        self.assertFalse(self.machine.done, "Machine crashed during start")

    def _mock_event_handler(self, event_name, **kwargs):
        del kwargs
        self._events[event_name] += 1

    def mock_event(self, event_name):
        self._events[event_name] = 0
        self.machine.events.add_handler(event=event_name,
                                        handler=self._mock_event_handler,
                                        event_name=event_name)

    def reset_mock_events(self):
        for event in self._events.keys():
            self._events[event] = 0

    def hit_switch_and_run(self, name, delta):
        self.machine.switch_controller.process_switch(name, 1)
        self.advance_time_and_run(delta)

    def release_switch_and_run(self, name, delta):
        self.machine.switch_controller.process_switch(name, 0)
        self.advance_time_and_run(delta)

    def hit_and_release_switch(self, name):
        self.machine.switch_controller.process_switch(name, 1)
        self.machine.switch_controller.process_switch(name, 0)
        self.machine_run()

    def tearDown(self):
        duration = time.time() - self.test_start_time
        if duration > self.expected_duration:
            print("Test {}.{} took {} > {}s".format(self.__class__,
                  self._testMethodName, round(duration, 2),
                  self.expected_duration))

        self.machine.log.debug("Test ended")
        if sys.exc_info != (None, None, None):
            # disable teardown logging after error
            logging.basicConfig(level=99)
        else:
            # fire all delays
            self.min_frame_time = 20.0
            self.advance_time_and_run(300)
        self.machine.clock.time = self.realTime
        self.machine.stop()
        self.machine = None
        self.realTime = None

        self.restore_sys_path()

    def patch_bcp(self):
        self.sent_bcp_commands = list()
        self.machine.bcp.send = self._bcp_send

    def _bcp_send(self, bcp_command, callback=None, **kwargs):
        self.sent_bcp_commands.append((bcp_command, callback, kwargs))

    def add_to_config_validator(self, key, new_dict):
        if mpf.core.config_validator.ConfigValidator.config_spec:
            mpf.core.config_validator.ConfigValidator.config_spec[key] = (
                new_dict)
        else:
            mpf.core.config_validator.mpf_config_spec += '\n' + yaml.dump(
                dict(key=new_dict), default_flow_style=False)
