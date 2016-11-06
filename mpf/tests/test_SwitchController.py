from unittest.mock import MagicMock

from mpf.core.switch_controller import MonitoredSwitchChange

from mpf.tests.MpfTestCase import MpfTestCase


class TestSwitchController(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/switch_controller/'

    def _callback(self, state, ms, switch_name):
        assert(switch_name == "s_test")
        assert(ms == 300)
        assert(state == 1)
        self.isActive = self.machine.switch_controller.is_active("s_test", ms=300)

    def test_monitor(self):
        # add monitor
        monitor = MagicMock()
        self.machine.switch_controller.add_monitor(monitor)

        # hit
        self.hit_switch_and_run("s_test", 1)
        monitor.assert_called_with(MonitoredSwitchChange(
            name='s_test', label='%', platform=self.machine.default_platform, num='1', state=1))
        monitor.reset_mock()

        # release
        self.release_switch_and_run("s_test", 1)
        monitor.assert_called_with(MonitoredSwitchChange(
            name='s_test', label='%', platform=self.machine.default_platform, num='1', state=0))
        monitor.reset_mock()

        # test unknown switch
        self.machine.switch_controller.process_switch_by_num(123123123, 1, self.machine.default_platform)
        monitor.assert_called_with(MonitoredSwitchChange(name='123123123', label='<Platform.Virtual>-123123123',
                                                         platform=self.machine.default_platform, num='123123123',
                                                         state=1))
        monitor.reset_mock()

        # remove monitor
        self.machine.switch_controller.remove_monitor(monitor)

        # no more events
        self.hit_switch_and_run("s_test", 1)
        monitor.assert_not_called()

    def test_wait_futures(self):
        self.hit_switch_and_run("s_test", 1)
        future = self.machine.switch_controller.wait_for_switch("s_test")
        future2 = self.machine.switch_controller.wait_for_switch("s_test", only_on_change=False)
        future3 = self.machine.switch_controller.wait_for_switch("s_test")
        future3.cancel()
        self.assertTrue(future2.done())
        self.release_switch_and_run("s_test", 1)
        self.assertFalse(future.done())
        self.hit_switch_and_run("s_test", 1)
        self.assertTrue(future.done())

    def test_verify_switches(self):
        self.assertTrue(self.machine.switch_controller.verify_switches())

    def test_is_active_timing(self):
        self.isActive = None

        self.machine.switch_controller.add_switch_handler(
                switch_name="s_test",
                callback=self._callback,
                state=1, ms=300, return_info=True)
        self.machine.switch_controller.process_switch("s_test", 1, True)

        self.advance_time_and_run(3)

        self.assertEqual(True, self.isActive)

    def test_initial_state(self):
        # tests that when MPF starts, the initial states of switches that
        # started in that state are read correctly.
        self.assertFalse(self.machine.switch_controller.is_active('s_test',
                                                                  1000))

    def _callback_invalid(self):
         raise AssertionError("Should not be called")

    def test_timed_switch_handler(self):
        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(3)

        self.machine.switch_controller.add_switch_handler(
                switch_name="s_test",
                callback=self._callback_invalid,
                state=0, ms=250)

        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.remove_switch_handler(
                switch_name="s_test",
                callback=self._callback_invalid,
                state=0, ms=250)

        self.advance_time_and_run(5)

        cb = MagicMock()
        self.hit_switch_and_run("s_test", .1)
        self.machine.switch_controller.add_switch_handler(
            switch_name="s_test",
            callback=cb,
            state=1, ms=300)
        cb.assert_not_called()
        self.advance_time_and_run(.1)
        cb.assert_not_called()
        self.advance_time_and_run(.1)
        cb.assert_called_with()

        cb = MagicMock()
        self.release_switch_and_run("s_test", .1)
        self.machine.switch_controller.add_switch_handler(
            switch_name="s_test",
            callback=cb,
            state=0, ms=300)
        cb.assert_not_called()
        self.advance_time_and_run(.1)
        cb.assert_not_called()
        self.advance_time_and_run(.1)
        cb.assert_called_with()

    def test_activation_and_deactivation_events(self):
        self.mock_event("test_active")
        self.mock_event("test_active2")
        self.mock_event("test_inactive")
        self.mock_event("test_inactive2")

        self.machine.switch_controller.process_switch("s_test_events", 1)
        self.machine_run()

        self.assertEqual(0, self._events['test_active'])
        self.assertEqual(1, self._events['test_active2'])
        self.assertEqual(0, self._events['test_inactive'])
        self.assertEqual(0, self._events['test_inactive2'])

        self.advance_time_and_run(1)

        self.assertEqual(1, self._events['test_active'])
        self.assertEqual(1, self._events['test_active2'])
        self.assertEqual(0, self._events['test_inactive'])
        self.assertEqual(0, self._events['test_inactive2'])

        self.machine.switch_controller.process_switch("s_test_events", 1)
        self.advance_time_and_run(1)

        self.assertEqual(1, self._events['test_active'])
        self.assertEqual(1, self._events['test_active2'])
        self.assertEqual(0, self._events['test_inactive'])
        self.assertEqual(0, self._events['test_inactive2'])

        self.machine.switch_controller.process_switch("s_test_events", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, self._events['test_active'])
        self.assertEqual(1, self._events['test_active2'])
        self.assertEqual(1, self._events['test_inactive'])
        self.assertEqual(0, self._events['test_inactive2'])

        self.advance_time_and_run(1)
        self.assertEqual(1, self._events['test_active'])
        self.assertEqual(1, self._events['test_active2'])
        self.assertEqual(1, self._events['test_inactive'])
        self.assertEqual(1, self._events['test_inactive2'])

    def test_ignore_window_ms(self):
        # first hit. switch gets active
        self.machine.switch_controller.process_switch("s_test_window_ms", 1)
        self.advance_time_and_run(.001)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_window_ms"))

        # an disables instantly
        self.machine.switch_controller.process_switch("s_test_window_ms", 0)
        self.advance_time_and_run(.001)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_window_ms"))

        # and enables again
        self.machine.switch_controller.process_switch("s_test_window_ms", 1)
        self.advance_time_and_run(.01)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_window_ms"))
        self.advance_time_and_run(.05)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_window_ms"))
        self.advance_time_and_run(.05)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_window_ms"))

    def test_invert(self):
        self.machine.switch_controller.process_switch("s_test_invert", 1, logical=False)
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active("s_test_invert"))

        self.machine.switch_controller.process_switch("s_test_invert", 1, logical=True)
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active("s_test_invert"))

        self.machine.switch_controller.process_switch("s_test_invert", 0, logical=False)
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active("s_test_invert"))

        self.machine.switch_controller.process_switch("s_test_invert", 0, logical=True)
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active("s_test_invert"))

    def _cb1a(self, **kwargs):
        del kwargs
        self.called1 = 1
        self.machine.switch_controller.remove_switch_handler("s_test", self._cb1a)

    def _cb2(self, **kwargs):
        del kwargs
        self.called2 = 1

    def _cb1b(self, **kwargs):
        del kwargs
        self.called1 = 1
        self.machine.switch_controller.remove_switch_handler("s_test", self._cb2)

    def test_remove_in_handler(self):
        self.called1 = 0
        self.called2 = 0
        self.machine.switch_controller.add_switch_handler("s_test", self._cb1a)
        self.machine.switch_controller.add_switch_handler("s_test", self._cb2)

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run()
        self.assertEqual(1, self.called1)
        self.assertEqual(1, self.called2)

    def test_remove_in_handler2(self):
        self.called1 = 0
        self.called2 = 0
        self.machine.switch_controller.add_switch_handler("s_test", self._cb1b)
        self.machine.switch_controller.add_switch_handler("s_test", self._cb2)

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run()
        self.assertEqual(1, self.called1)
        self.assertEqual(0, self.called2)

    def _cb3(self, **kwargs):
        del kwargs
        self.called3 = 1

    def test_active_and_inactive_times(self):
        # Regression test for switch_controller bug in _cancel_timed_handlers
        self.machine.switch_controller.add_switch_handler("s_test", self._cb2, ms=5000, state=1)
        self.machine.switch_controller.add_switch_handler("s_test_events", self._cb2, ms=5000, state=1)

        self.called2 = 0
        self.machine.switch_controller.process_switch("s_test", 1)
        self.machine.switch_controller.process_switch("s_test_events", 1)

        self.advance_time_and_run(2)
        self.called2 = 0
        self.machine.switch_controller.process_switch("s_test", 0)
        self.machine.switch_controller.process_switch("s_test_events", 1)

        self.advance_time_and_run(5)
        self.assertEqual(1, self.called2)
