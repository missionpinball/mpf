"""Baseclass for all tests."""
import copy
import inspect
import logging
import os
import sys
import time
import unittest

from unittest.mock import *

import asyncio
from asyncio import events
import ruamel.yaml as yaml
from mpf.core.rgb_color import RGBColor

from mpf.tests.TestDataManager import TestDataManager
from mpf.tests.loop import TimeTravelLoop, TestClock

import mpf.core
import mpf.core.config_validator
from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util
from mpf.file_interfaces.yaml_interface import YamlInterface

YamlInterface.cache = True


class TestMachineController(MachineController):

    """MachineController used in tests."""

    local_mpf_config_cache = {}

    def __init__(self, mpf_path, machine_path, options, config_patches, clock, mock_data,
                 enable_plugins=False):
        self.test_config_patches = config_patches
        self.test_init_complete = False
        self._enable_plugins = enable_plugins
        self._test_clock = clock
        self._mock_data = mock_data
        super().__init__(mpf_path, machine_path, options)

    def create_data_manager(self, config_name):
        return TestDataManager(self._mock_data.get(config_name, {}))

    def _load_clock(self):
        return self._test_clock

    def __del__(self):
        if self._test_clock:
            self._test_clock.loop.close()

    def sleep_until_next_event_mock(self):
        for socket, callback in self.clock.read_sockets.items():
            if socket.ready():
                callback()

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
        self._get_event_loop = None
        self._get_event_loop2 = None

        super().__init__(methodName)
        self.machine = None     # type: TestMachineController
        self.machine_config_patches = dict()
        self.machine_config_patches['mpf'] = dict()
        self.machine_config_patches['mpf']['default_platform_hz'] = 100
        self.machine_config_patches['mpf']['plugins'] = list()
        self.machine_config_patches['bcp'] = []
        self._last_event_kwargs = {}
        self._events = {}
        self.expected_duration = 0.5
        self.min_frame_time = 1 / 30  # test with default Hz

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

    def advance_time_and_run(self, delta=1.0):
        self.machine.log.info("Advancing time by %s", delta)
        try:
            self.loop.run_until_complete(asyncio.sleep(delay=delta, loop=self.loop))
            return
        except RuntimeError as e:
            if self._exception:
                raise self._exception['exception']
            raise e

    def machine_run(self):
        self.advance_time_and_run(0)

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

        # make tests path independent. remove current dir absolue
        if os.curdir in sys.path:
            sys.path.remove(os.curdir)

        # make tests path independent. remove current dir relative
        if "" in sys.path:
            sys.path.remove("")

    def restore_sys_path(self):
        # restore sys path
        sys.path = self._sys_path

    def _get_mock_data(self):
        """Return data for MockDataMangager in test."""
        return dict()

    def _mock_loop(self):
        pass

    def _exception_handler(self, loop, context):
        loop.stop()
        self._exception = context

    def setUp(self):
        self._get_event_loop = asyncio.get_event_loop
        asyncio.get_event_loop = None
        self._get_event_loop2 = asyncio.events.get_event_loop
        events.get_event_loop = None

        # we want to reuse config_specs to speed tests up
        mpf.core.config_validator.ConfigValidator.unload_config_spec = (
            MagicMock())

        self._events = {}
        self._last_event_kwargs = {}
        self._exception = None

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

        self.loop = TimeTravelLoop()
        self.loop.set_exception_handler(self._exception_handler)
        self.clock = TestClock(self.loop)
        self._mock_loop()

        try:
            self.machine = TestMachineController(
                os.path.abspath(os.path.join(
                    mpf.core.__path__[0], os.pardir)), machine_path,
                self.getOptions(), self.machine_config_patches, self.clock, self._get_mock_data(),
                self.get_enable_plugins())

            start = time.time()
            while not self.machine.test_init_complete and time.time() < start + 20:
                self.advance_time_and_run(0.01)

            self.machine.events.process_event_queue()
            self.advance_time_and_run(1)

        except Exception as e:
            # todo temp until I can figure out how to stop the asset loader
            # thread automatically.
            try:
                self.machine.stop()
            except AttributeError:
                pass
            raise e

        self.assertFalse(self.machine._done, "Machine crashed during start")

    def _mock_event_handler(self, event_name, **kwargs):
        self._last_event_kwargs[event_name] = kwargs
        self._events[event_name] += 1

    def mock_event(self, event_name):
        self._events[event_name] = 0
        self.machine.events.remove_handler_by_event(event=event_name, handler=self._mock_event_handler)
        self.machine.events.add_handler(event=event_name,
                                        handler=self._mock_event_handler,
                                        event_name=event_name)

    def assertLedColor(self, led_name, color):
        self.assertEqual(list(RGBColor(color).rgb), self.machine.leds[led_name].hw_driver.current_color)

    def assertModeRunning(self, mode_name):
        if mode_name not in self.machine.modes:
            raise AssertionError("Mode {} not known.".format(mode_name))
        self.assertIn(self.machine.modes[mode_name], self.machine.mode_controller.active_modes,
                      "Mode {} not running.".format(mode_name))

    def assertModeNotRunning(self, mode_name):
        if mode_name not in self.machine.modes:
            raise AssertionError("Mode {} not known.".format(mode_name))
        self.assertNotIn(self.machine.modes[mode_name], self.machine.mode_controller.active_modes,
                         "Mode {} running but should not.".format(mode_name))

    def assertEventNotCalled(self, event_name):
        """Assert that event was not called."""
        if event_name not in self._events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._events[event_name] != 0:
            raise AssertionError("Event {} was called {} times.".format(event_name, self._events[event_name]))

    def assertEventCalled(self, event_name, times=None):
        """Assert that event was called."""
        if event_name not in self._events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._events[event_name] == 0 and times != 0:
            raise AssertionError("Event {} was not called.".format(event_name))

        if times is not None and self._events[event_name] != times:
            raise AssertionError("Event {} was called {} instead of {}.".format(
                event_name, self._events[event_name], times))

    def assertEventCalledWith(self, event_name, **kwargs):
        """Assert that event was called with kwargs."""
        self.assertEventCalled(event_name)
        self.assertEqual(kwargs, self._last_event_kwargs[event_name], "Args for {} differ.".format(event_name))

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
        self.machine.stop()
        self.machine._do_stop()
        self.machine.clock.loop.close()
        self.machine = None

        self.restore_sys_path()
        asyncio.get_event_loop = self._get_event_loop
        self._get_event_loop = None
        events.get_event_loop = self._get_event_loop2
        self._get_event_loop2 = None

    def add_to_config_validator(self, key, new_dict):
        if mpf.core.config_validator.ConfigValidator.config_spec:
            mpf.core.config_validator.ConfigValidator.config_spec[key] = (
                new_dict)
        else:
            mpf.core.config_validator.mpf_config_spec += '\n' + yaml.dump(
                {key: new_dict}, default_flow_style=False)
