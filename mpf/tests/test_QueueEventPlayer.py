"""Test queue event player."""
from mpf.tests.MpfTestCase import MpfTestCase


class TestQueueEventPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'test_queue_event_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/event_players/'

    def _queue1(self, queue, **kwargs):
        del kwargs
        queue.wait()
        self.queue1 = queue

    def _queue2(self, queue, **kwargs):
        del kwargs
        queue.wait()
        self.queue2 = queue

    def test_queue_event_player(self):
        self.mock_event("queue_event1_finished")
        self.queue1 = None
        self.queue2 = None
        self.machine.events.add_handler("queue_event1", self._queue1, priority=2)
        self.machine.events.add_handler("queue_event1", self._queue2, priority=1)
        self.post_event("play")
        self.advance_time_and_run()

        self.assertIsNotNone(self.queue1)
        self.assertIsNone(self.queue2)

        self.queue1.clear()
        self.advance_time_and_run()
        self.assertIsNotNone(self.queue2)
        self.assertEventNotCalled("queue_event1_finished")

        self.queue2.clear()
        self.advance_time_and_run()
        self.assertEventCalled("queue_event1_finished")

    def _cb(self, **kwargs):
        del kwargs
        self._done = True

    def test_queue_relay_player(self):
        self._done = False
        self.mock_event("relay_start")
        self.mock_event("relay2_start")

        # post queue event
        self.machine.events.post_queue("relay", callback=self._cb, something=7)
        self.advance_time_and_run()

        # should run the first relay only
        self.assertFalse(self._done)
        self.assertEventCalledWith("relay_start")
        self.assertEventNotCalled("relay2_start")

        # first relay done. should trigger the second
        self.post_event("relay_done")
        self.advance_time_and_run()
        self.assertEventCalled("relay2_start")
        self.assertFalse(self._done)

        # second done. should trigger cb
        self.post_event("relay2_done")
        self.advance_time_and_run()
        self.assertTrue(self._done)

    def test_queue_relay_player_with_pass_args(self):
        self._done = False
        self.mock_event("relay_with_args_start")

        # post queue event
        self.machine.events.post_queue("relay_with_args", callback=self._cb, test=42)
        self.advance_time_and_run()

        # should run the first relay only
        self.assertFalse(self._done)
        self.assertEventCalledWith("relay_with_args_start", test=42)

        # relay done
        self.post_event("relay_with_args_done")
        self.advance_time_and_run()
        self.assertTrue(self._done)

    def test_broken_queue_relay_player(self):
        with self.assertRaises(Exception) as e:
            self.post_event("relay")
        self.assertIsInstance(e.exception.__cause__, AssertionError)
        self.assertEqual(str(e.exception.__cause__), "Can only use queue relay player with queue event.")

        # reset exception
        self._exception = None

    def test_queue_relay_player_in_mode(self):
        self._done = False
        self.mock_event("relay3_start")

        self.machine.modes.mode1.start()

        # post queue event
        self.machine.events.post_queue("relay3", callback=self._cb)
        self.advance_time_and_run()

        # should run the relay
        self.assertFalse(self._done)
        self.assertEventCalled("relay3_start")

        # relay done. should trigger cb
        self.post_event("relay3_done")
        self.advance_time_and_run()
        self.assertTrue(self._done)

        # stop and start mode again
        self.machine.modes.mode1.stop()
        self.advance_time_and_run()

        self._done = False
        self.mock_event("relay3_start")
        self.machine.modes.mode1.start()

        # post queue event
        self.machine.events.post_queue("relay3", callback=self._cb)
        self.advance_time_and_run()

        # should run the relay
        self.assertFalse(self._done)
        self.assertEventCalled("relay3_start")

        # relay done. should trigger cb
        self.post_event("relay3_done")
        self.advance_time_and_run()
        self.assertTrue(self._done)

        # post queue event again
        self._done = False
        self.machine.events.post_queue("relay3", callback=self._cb)
        self.advance_time_and_run()
        self.assertFalse(self._done)

        # stop mode
        self.machine.modes.mode1.stop()
        self.advance_time_and_run()

        # should trigger cb without waiting for event
        self.assertTrue(self._done)

        # relay should not crash it
        self.post_event("relay3_done")
        self.advance_time_and_run()
