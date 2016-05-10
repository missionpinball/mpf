from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestDelay(MpfTestCase):

    def callback(self):
        pass

    def testBasicFunctions(self):
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
