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
from typing import Any

from mpf.core.logging import LogMixin
from mpf.core.rgb_color import RGBColor

from mpf.tests.TestDataManager import TestDataManager
from mpf.tests.loop import TimeTravelLoop, TestClock

import mpf.core
import mpf.core.config_validator
from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util
from mpf.file_interfaces.yaml_interface import YamlInterface

YamlInterface.cache = True


def test_config(config_file):

    """Decorator to overwrite config file for one test."""

    def test_decorator(fn):
        """Decorate function."""
        fn.config_file = config_file
        return fn
    return test_decorator


def test_config_directory(config_directory):

    """Decorator to overwrite config directory for one test."""

    def test_decorator(fn):
        """Decorate function."""
        fn.config_directory = config_directory
        return fn
    return test_decorator


class TestMachineController(MachineController):

    """A patched version of the MachineController used in tests.

    The TestMachineController has a few changes from the regular machine
    controller to facilitate running unit tests, including:

    * Use the TestDataManager instead of the real one.
    * Use a test clock which we can manually advance instead of the regular
      clock tied to real-world time.
    * Only load plugins if ``self._enable_plugins`` is *True*.
    * Merge any ``test_config_patches`` into the machine config.
    * Disabled the config file caching to always load the config from disk.

    """
    local_mpf_config_cache = {}     # type: Any

    def __init__(self, mpf_path, machine_path, options, config_patches, config_defaults, clock, mock_data,
                 enable_plugins=False, early_init=None):
        self.test_config_patches = config_patches
        self.test_config_defaults = config_defaults
        self._enable_plugins = enable_plugins
        self._test_clock = clock
        self._mock_data = mock_data
        self._early_init = early_init
        super().__init__(mpf_path, machine_path, options)

    def create_data_manager(self, config_name):
        """Create TestDataManager."""
        return TestDataManager(self._mock_data.get(config_name, {}))

    def _load_clock(self):
        return self._test_clock

    def __del__(self):
        if self._test_clock:
            self._test_clock.loop.close()

    def _register_plugin_config_players(self):
        if self._enable_plugins:
            super()._register_plugin_config_players()

    def _load_config(self):
        if self._early_init:
            self._early_init(self)
        super()._load_config()
        self.config = Util.dict_merge(self.test_config_defaults, self.config)
        self.config = Util.dict_merge(self.config, self.test_config_patches)


class MpfTestCase(unittest.TestCase):

    """Primary TestCase class used for all MPF unit tests."""

    def __init__(self, methodName='runTest'):
        self._get_event_loop = None
        self._get_event_loop2 = None

        LogMixin.unit_test = True

        super().__init__(methodName)
        self.machine = None     # type: TestMachineController
        self.machine_config_patches = dict()
        self.machine_config_patches['mpf'] = dict()
        self.machine_config_patches['mpf']['default_platform_hz'] = 100
        self.machine_config_patches['mpf']['plugins'] = list()
        self.machine_config_patches['bcp'] = []

        self.machine_config_defaults = dict()
        self.machine_config_defaults['playfields'] = dict()
        self.machine_config_defaults['playfields']['playfield'] = dict()
        self.machine_config_defaults['playfields']['playfield']['tags'] = "default"
        self.machine_config_defaults['playfields']['playfield']['default_source_device'] = None

        self._last_event_kwargs = {}
        self._events = {}
        self.expected_duration = 0.5

    def start_mode(self, mode):
        """Start mode."""
        self.assertIn(mode, self.machine.modes)
        self.assertModeNotRunning(mode)
        self.machine.modes[mode].start()
        self.machine_run()
        self.assertModeRunning(mode)

    def stop_mode(self, mode):
        """Stop mode."""
        self.assertModeRunning(mode)
        self.machine.modes[mode].stop()
        self.machine_run()
        self.assertModeNotRunning(mode)

    def getConfigFile(self):
        """Return a string name of the machine config file to use for the tests
        in this class.

        You should override this method in your own test class to point to the
        config file you need for your tests.

        Returns:
            A string name of the machine config file to use, complete with the
            ``.yaml`` file extension.

        For example:

        .. code::

            def getConfigFile(self):
                return 'my_config.yaml'

        """
        return 'null.yaml'

    def getMachinePath(self):
        """Return a string name of the path to the machine folder to use for
        the tests in this class.

        You should override this method in your own test class to point to the
        machine folder root you need for your tests.

        Returns:
            A string name of the machine path to use

        For example:

        .. code::

            def getMachinePath(self):
                return 'tests/machine_files/my_test/'

        Note that this path is relative to the MPF package root

        """
        return 'tests/machine_files/null/'

    def getAbsoluteMachinePath(self):
        """Return absolute machine path."""
        # check if there is a decorator
        config_directory = getattr(getattr(self, self._testMethodName), "config_directory", None)
        if not config_directory:
            config_directory = self.getMachinePath()

        # creates an absolute path based on machine_path
        return os.path.abspath(os.path.join(
            mpf.core.__path__[0], os.pardir, config_directory))

    @staticmethod
    def get_abs_path(path):
        return os.path.join(os.path.abspath(os.curdir), path)

    def post_event(self, event_name, run_time=0):
        """Post an MPF event and optionally advance the time.

        Args:
            event_name: String name of the event to post
            run_time: How much time (in seconds) the test should advance
                after this event has been posted.

        For example, to post an event called "shot1_hit":

        .. code::

            self.post_event('shot1_hit')

        To post an event called "tilt" and then advance the time 1.5 seconds:

        .. code::

            self.post_event('tilt', 1.5)

        """
        self.machine.events.post(event_name)
        self.advance_time_and_run(run_time)

    def post_event_with_params(self, event_name, **params):
        """Post an MPF event with kwarg parameters.

        Args:
            event_name: String name of the event to post
            **params: One or more kwarg key/value pairs to post with the event.

        For example, to post an event called "jackpot" with the parameters
        ``count=1`` and ``first_time=True``, you would use:

        .. code::

            self.post_event('jackpot', count=1, first_time=True)

        """
        self.machine.events.post(event_name, **params)
        self.machine_run()

    def post_relay_event_with_params(self, event_name, **params):
        """Post a relay event synchronously and return the result."""
        future = self.machine.events.post_relay_async(event_name, **params)
        result = self.machine.clock.loop.run_until_complete(future)
        return result

    def assertPlaceholderEvaluates(self, expected, condition):
        result = self.machine.placeholder_manager.build_raw_template(condition).evaluate([],
                                                                                         fail_on_missing_params=True)
        self.assertEqual(expected, result, "{} = {} != {}".format(condition, result, expected))

    def assertNumBallsKnown(self, balls):
        """Assert that a certain number of balls are known in the machine."""
        self.assertEqual(balls, self.machine.ball_controller.num_balls_known)

    def set_num_balls_known(self, balls):
        """Set the ball controller's ``num_balls_known`` attribute.

        This is needed for tests where you don't have any ball devices and
        other situations where you need the ball controller to think the
        machine has a certain amount of balls to run a test.

        Example:

        .. code::

            self.set_num_balls_known(3)


        """
        # in case the test does not have any ball devices
        self.machine.ball_controller.num_balls_known = balls

    def get_platform(self):
        """Force this test class to use a certain platform.

        Returns:
            String name of the platform this test class will use.

        If you don't include this method in your test class, the platform will
        be set to `virtual`. If you want to use the smart virtual platform,
        you would add the following to your test class:

        .. code::

            def get_platform(self):
                return 'smart_virtual`

        """
        return 'virtual'

    def get_use_bcp(self):
        """Control whether tests in this class should use BCP.

        Returns: True or False

        The default is False. To use BCP in your test class, add the following:

         .. code::

            def get_use_bcp(self):
                return True

        """
        return False

    def get_enable_plugins(self):
        """Control whether tests in this class should load MPF plugins.

        Returns: True or False

        The default is False. To load plugins in your test class, add the
        following:

         .. code::

            def get_enable_plugins(self):
                return True

        """
        return False

    def _getConfigFile(self):
        """Return test decorator value or the return of getConfigFile."""
        config_file = getattr(getattr(self, self._testMethodName), "config_file", None)
        if config_file:
            return config_file
        else:
            return self.getConfigFile()

    def getOptions(self):

        mpfconfig = os.path.abspath(os.path.join(
            mpf.core.__path__[0], os.pardir, 'mpfconfig.yaml'))

        return {
            'force_platform': self.get_platform(),
            'production': False,
            'mpfconfigfile': mpfconfig,
            'configfile': Util.string_to_list(self._getConfigFile()),
            'debug': True,
            'bcp': self.get_use_bcp(),
            'no_load_cache': False,
            'create_config_cache': True,
            'text_ui': False,
        }

    def advance_time_and_run(self, delta=1.0):
        """Advance the test clock and run anything that should run during that
        time.

        Args:
            delta: How much time to advance the test clock by (in seconds)

        This method will cause anything scheduled during the time to run,
        including things like delays, timers, etc.

        Advancing the clock will happen in multiple small steps if things are
        scheduled to happen during this advance. For example, you can advance
        the clock 10 seconds like this:

        .. code::

            self.advance_time_and_run(10)

        If there is a delay callback that is scheduled to happen in 2 seconds,
        then this method will advance the clock 2 seconds, process that delay,
        and then advance the remaining 8 seconds.

        """
        self.machine.log.info("Advancing time by %s", delta)
        try:
            self.loop.run_until_complete(asyncio.sleep(delay=delta, loop=self.loop))
            return
        except RuntimeError as e:
            try:
                self.machine.stop()
            except Exception:
                pass
            if self._exception and "exception" in self._exception:
                exception = self._exception['exception']
                self._exception = None
                raise exception
            elif self._exception:
                exception = self._exception['exception']
                self._exception = None
                raise Exception(exception, e)
            raise e

    def machine_run(self):
        """Process any delays, timers, or anything else scheduled.

        Note this is the same as:

        .. code::

            self.advance_time_and_run(0)

        """
        self.advance_time_and_run(0)

    @staticmethod
    def unittest_verbosity():
        """Return the verbosity setting of the currently running unittest
        program, or 0 if none is running.

        Returns: An integer value of the current verbosity setting.

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

    def _early_machine_init(self, machine):
        pass

    def _exception_handler(self, loop, context):
        try:
            loop.stop()
        except RuntimeError:
            pass

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
                self.getOptions(), self.machine_config_patches, self.machine_config_defaults,
                self.clock, self._get_mock_data(),
                self.get_enable_plugins(), self._early_machine_init)

            self._initialise_machine()

        # pylint: disable-msg=broad-except
        except Exception as e:
            try:
                self.machine.stop()
            except AttributeError:
                pass
            if self._exception and 'exception' in self._exception:
                raise self._exception['exception']
            elif self._exception:
                raise Exception(self._exception, e)
            raise e

    def _initialise_machine(self):
        init = Util.ensure_future(self.machine.initialise(), loop=self.loop)
        self._wait_for_start(init, 20)
        self.machine.events.process_event_queue()
        self.advance_time_and_run(1)

    def _wait_for_start(self, init, timeout):
        start = time.time()
        while not init.done() and not self._exception:
            self.loop._run_once()
            if time.time() > start + timeout:
                raise AssertionError("Start took more than {}s".format(timeout))

        # trigger exception if there was one
        init.result()

    def _mock_event_handler(self, event_name, **kwargs):
        self._last_event_kwargs[event_name] = kwargs
        self._events[event_name] += 1

    def mock_event(self, event_name):
        """Configure an event to be mocked.

        Args:
            event_name: String name of the event to mock.

        Mocking an event is an easy way to check if an event was called without
        configuring some kind of callback action in your tests.

        Note that an event must be mocked here *before* it's posted in order
        for :meth:`assertEventNotCalled` and :meth:`assertEventCalled` to work.

        Mocking an event will not "break" it. In other words, any other
        registered handlers for this event will also be called even if the
        event has been mocked.

        For example:

        .. code::

            self.mock_event('my_event')
            self.assertEventNotCalled('my_event')  # This will be True
            self.post_event('my_event')
            self.assertEventCalled('my_event')  # This will also be True

        """
        self._events[event_name] = 0
        self.machine.events.remove_handler_by_event(event=event_name, handler=self._mock_event_handler)
        self.machine.events.add_handler(event=event_name,
                                        handler=self._mock_event_handler,
                                        event_name=event_name)

    def assertBallsOnPlayfield(self, balls, playfield="playfield"):
        self.assertEqual(balls, self.machine.playfields[playfield].balls)

    def assertAvailableBallsOnPlayfield(self, balls, playfield="playfield"):
        self.assertEqual(balls, self.machine.playfields[playfield].available_balls)

    def assertMachineVarEqual(self, value, machine_var):
        self.assertTrue(self.machine.is_machine_var(machine_var), "Machine Var {} does not exist.".format(machine_var))
        self.assertEqual(value, self.machine.get_machine_var(machine_var))

    def assertPlayerVarEqual(self, value, player_var):
        self.assertIsNotNone(self.machine.game, "There is no game.")
        self.assertEqual(value, self.machine.game.player[player_var], "Value of player var {} is {} but should be {}".
                         format(player_var, self.machine.game.player[player_var], value))

    def assertSwitchState(self, name, state):
        self.assertIn(name, self.machine.switches, "Switch {} does not exist.".format(name))
        self.assertEqual(state, self.machine.switch_controller.is_active(name),
                         "Switch {} is in state {} != {}".format(name, self.machine.switch_controller.is_active(name),
                                                                 state))

    def assertLightChannel(self, light_name, brightness, channel="white"):
        self.assertAlmostEqual(brightness / 255.0, self.machine.lights[light_name].hw_drivers[channel][0].
                               current_brightness)

    def assertNotLightChannel(self, light_name, brightness, channel="white"):
        self.assertNotEqual(brightness, self.machine.lights[light_name].hw_drivers[channel][0].
                            current_brightness)

    def assertLightColor(self, light_name, color):
        if isinstance(color, str) and color.lower() == 'on':
            color = self.machine.lights[light_name].config['default_on_color']

        self.assertEqual(RGBColor(color), self.machine.lights[light_name].get_color(),
                         "{} != {}".format(RGBColor(color).name, self.machine.lights[light_name].get_color().name))

    def assertNotLightColor(self, light_name, color):
        if isinstance(color, str) and color.lower() == 'on':
            color = self.machine.lights[light_name].config['default_on_color']

        self.assertNotEqual(RGBColor(color), self.machine.lights[light_name].get_color(),
                            "{} == {}".format(RGBColor(color).name, self.machine.lights[light_name].get_color().name))

    def assertLightColors(self, light_name, color_list, secs=1, check_delta=.1):
        colors = list()

        # have to do it this weird way because `if 'on' in color_list:` doesn't
        # work since it tries to convert it to a color
        for color in color_list[:]:
            if isinstance(color, str) and color.lower() == 'on':
                color_list.remove('on')
                color_list.append(self.machine.lights[light_name].config['default_on_color'])
                break

        for x in range(int(secs / check_delta)):
            color = self.machine.lights[light_name].get_color()
            colors.append(color)
            self.advance_time_and_run(check_delta)

        for color in color_list:
            self.assertIn(RGBColor(color), colors)

    def assertLightOn(self, light_name):
        self.assertEqual(255,
                         self.machine.lights[
                             light_name].hw_driver.current_brightness)

    def assertLightOff(self, light_name):
        self.assertEqual(0, self.machine.lights[light_name].hw_driver.current_brightness)

    def assertLightFlashing(self, light_name, color=None, secs=1, check_delta=.1):
        brightness_values = list()
        if not color:
            color = [255, 255, 255]

        for _ in range(int(secs / check_delta)):
            brightness_values.append(
                self.machine.lights[light_name].get_color())
            self.advance_time_and_run(check_delta)

        self.assertIn([0, 0, 0], brightness_values)
        self.assertIn(color, brightness_values)

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
        """Assert that event was not called.

        Args:
            event_name: String name of the event to check.

        Note that the event must be mocked via ``self.mock_event()`` first in
        order to use this method.

        """
        if event_name not in self._events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._events[event_name] != 0:
            raise AssertionError("Event {} was called {} times.".format(event_name, self._events[event_name]))

    def assertEventCalled(self, event_name, times=None):
        """Assert that event was called.

        Args:
            event_name: String name of the event to check.
            times: An optional value to confirm the number of times the event
                was called. Default of *None* means this method will pass as
                long as the event has been called at least once.

        If you want to reset the ``times`` count, you can mock the event
        again.

        Note that the event must be mocked via ``self.mock_event()`` first in
        order to use this method.

        For example:

        .. code::

            self.mock_event('my_event')
            self.assertEventNotCalled('my_event')  # This will pass

            self.post_event('my_event')
            self.assertEventCalled('my_event')     # This will pass
            self.assertEventCalled('my_event', 1)  # This will pass

            self.post_event('my_event')
            self.assertEventCalled('my_event')     # This will pass
            self.assertEventCalled('my_event', 2)  # This will pass

        """
        if event_name not in self._events:
            raise AssertionError("Event {} not mocked.".format(event_name))

        if self._events[event_name] == 0 and times != 0:
            raise AssertionError("Event {} was not called.".format(event_name))

        if times is not None and self._events[event_name] != times:
            raise AssertionError("Event {} was called {} instead of {}.".format(
                event_name, self._events[event_name], times))

    def assertEventCalledWith(self, event_name, **kwargs):
        """Assert an event was called with certain kwargs.

        Args:
            event_name: String name of the event to check.
            **kwargs: Name/value parameters to check.

        For example:

        .. code::

            self.mock_event('jackpot')

            self.post_event('jackpot', count=1, first_time=True)
            self.assertEventCalled('jackpot')  # This will pass
            self.assertEventCalledWith('jackpot', count=1, first_time=True)  # This will also pass
            self.assertEventCalledWith('jackpot', count=1, first_time=False)  # This will fail


        """
        self.assertEventCalled(event_name)
        self.assertEqual(kwargs, self._last_event_kwargs[event_name], "Args for {} differ.".format(event_name))

    def assertColorAlmostEqual(self, color1, color2, delta=6):
        """Assert that two color are almost equal.

        Args:
            color1: The first color, as an RGBColor instance or 3-item iterable.
            color2: The second color, as an RGBColor instance or 3-item iterable.
            delta: How close the colors have to be. The deltas between red,
                green, and blue are added together and must be less or equal
                to this value for this assertion to succeed.

        """
        if isinstance(color1, RGBColor) and isinstance(color2, RGBColor):
            difference = abs(color1.red - color2.red) +\
                abs(color1.blue - color2.blue) +\
                abs(color1.green - color2.green)
        else:
            difference = abs(color1[0] - color2[0]) +\
                abs(color1[1] - color2[1]) +\
                abs(color1[2] - color2[2])
        self.assertLessEqual(difference, delta, "Colors do not match: " + str(color1) + " " + str(color2))

    def reset_mock_events(self):
        """Reset all mocked events.

        This will reset the count of number of times called every mocked
        event is.

        """
        for event in self._events.keys():
            self._events[event] = 0

    def hit_switch_and_run(self, name, delta):
        """Activates a switch and advances the time.

        Args:
            name: The name of the switch to activate.
            delta: The time (in seconds) to advance the clock.

        Note that this method does not deactivate the switch once the time
        has been advanced, meaning the switch stays active. To make the
        switch inactive, use the :meth:`release_switch_and_run`.

        """
        self.machine.switch_controller.process_switch(name, state=1, logical=True)
        self.advance_time_and_run(delta)

    def release_switch_and_run(self, name, delta):
        """Deactivates a switch and advances the time.

        Args:
            name: The name of the switch to activate.
            delta: The time (in seconds) to advance the clock.

        """
        self.machine.switch_controller.process_switch(name, state=0, logical=True)
        self.advance_time_and_run(delta)

    def hit_and_release_switch(self, name):
        """Momentarily activates and then deactivates a switch.

        Args:
            name: The name of the switch to hit.

        This method immediately activates and deactivates a switch with no
        time in between.

        """
        self.machine.switch_controller.process_switch(name, state=1, logical=True)
        self.machine.switch_controller.process_switch(name, state=0, logical=True)
        self.machine_run()

    def hit_and_release_switches_simultaneously(self, names):
        """Momentarily activates and then deactivates multiple switches.

        Switches are hit sequentially and then released sequentially.
        Events are only processed at the end of the sequence which is useful
        to reproduce race conditions when processing nearly simultaneous hits.

        Args:
            names: The names of the switches to hit and release.

        """
        for name in names:
            self.machine.switch_controller.process_switch(name, state=1, logical=True)
        for name in names:
            self.machine.switch_controller.process_switch(name, state=0, logical=True)
        self.machine_run()

    def tearDown(self):
        if self._exception:
            try:
                self.machine.shutdown()
            except:
                pass

            if self._exception and 'exception' in self._exception:
                raise self._exception['exception']
            elif self._exception:
                raise Exception(self._exception)

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
            self.advance_time_and_run(300)
        self.machine._do_stop()
        self.machine = None

        self.restore_sys_path()
        asyncio.get_event_loop = self._get_event_loop
        self._get_event_loop = None
        events.get_event_loop = self._get_event_loop2
        self._get_event_loop2 = None

    @staticmethod
    def add_to_config_validator(machine, key, new_dict):
        """Add config dict to validator."""
        machine.config_validator.get_config_spec()[key] = new_dict
