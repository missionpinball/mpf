from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestDelay(MpfTestCase):

    def callback(self):
        pass

    def test_basic_functions(self):
        self.callback = MagicMock()
        self.assertEqual(len(self.machine.delay.delays), 0)

        # Create a one second delay
        self.machine.delay.add(1000, self.callback, "delay_test")
        self.assertEqual(len(self.machine.delay.delays), 1)
        self.assertIn("delay_test", self.machine.delay.delays.keys())

        # Advance 0.5 sec (callback should not have been called yet)
        self.advance_time_and_run(0.5)
        self.callback.assert_not_called()

        # Advance another 0.5 sec (callback should have been called)
        self.advance_time_and_run(0.5)
        self.callback.assert_called_with()
        self.assertEqual(len(self.machine.delay.delays), 0)
        self.assertNotIn("delay_test", self.machine.delay.delays.keys())

        # Create another one second delay
        self.callback.reset_mock()
        self.machine.delay.add(1000, self.callback, "delay_test2")
        self.assertEqual(len(self.machine.delay.delays), 1)
        self.assertIn("delay_test2", self.machine.delay.delays.keys())

        # Advance 0.5 sec (callback should not have been called yet)
        self.advance_time_and_run(0.5)
        self.callback.assert_not_called()

        # Now cancel the delay
        self.machine.delay.remove("delay_test2")
        self.assertEqual(len(self.machine.delay.delays), 0)
        self.assertNotIn("delay_test2", self.machine.delay.delays.keys())

        # Advance another 0.5 sec (callback should not be called since it was cancelled)
        self.advance_time_and_run(0.5)
        self.callback.assert_not_called()

    def test_remove(self):
        self.callback = MagicMock()
        self.machine.delay.add(1000, self.callback, "delay_test")

        self.assertTrue(self.machine.delay.check('delay_test'))
        self.machine.delay.remove('delay_test')
        self.advance_time_and_run(2)
        self.callback.assert_not_called()

    def test_check(self):
        self.callback = MagicMock()
        self.machine.delay.add(1000, self.callback, "delay_test")

        self.assertTrue(self.machine.delay.check('delay_test'))
        self.assertFalse(self.machine.delay.check('delay_test_fake'))

    def test_reset(self):
        self.callback = MagicMock()
        self.machine.delay.add(1000, self.callback, "delay_test")

        self.assertTrue(self.machine.delay.check('delay_test'))

        self.machine.delay.reset(2000, self.callback, "delay_test")

        self.advance_time_and_run(1.1)
        self.callback.assert_not_called()

        self.advance_time_and_run(1)
        self.callback.assert_any_call()

        # make sure reset works if there is no delay with that name
        self.machine.delay.reset(1000, self.callback, "delay_test2")
        self.advance_time_and_run(1.1)
        self.callback.assert_any_call()

    def test_clear(self):
        self.callback = MagicMock()
        self.machine.delay.add(1000, self.callback)
        self.machine.delay.add(2000, self.callback)

        self.machine.delay.clear()
        self.advance_time_and_run(3)

        self.callback.assert_not_called()

    def test_add_if_doesnt_exist(self):
        self.callback = MagicMock()
        self.machine.delay.add_if_doesnt_exist(1000, self.callback,
                                              "delay_test")

        self.advance_time_and_run(1.1)
        self.callback.assert_any_call()

        self.callback = MagicMock()
        self.machine.delay.add_if_doesnt_exist(1000, self.callback,
                                              "delay_test")
        self.machine.delay.add_if_doesnt_exist(500, self.callback,
                                      "delay_test")
        self.advance_time_and_run(.6)
        self.callback.assert_not_called()
        self.advance_time_and_run(.5)
        self.callback.assert_any_call()

    def test_run_now(self):
        self.callback = MagicMock()
        self.machine.delay.add(1000, self.callback, "delay_test")
        self.advance_time_and_run(.1)
        self.callback.assert_not_called()

        self.machine.delay.run_now("delay_test")
        self.advance_time_and_run(.1)
        self.callback.assert_any_call()

        self.callback = MagicMock()
        self.advance_time_and_run(1)
        self.callback.assert_not_called()
