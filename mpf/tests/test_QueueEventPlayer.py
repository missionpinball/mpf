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

    def test_load_and_play(self):
        self.mock_event("queue_event1_finished")
        self.queue1 = None
        self.queue2 = None
        self.machine.events.add_handler("queue_event1", self._queue1)
        self.machine.events.add_handler("queue_event1", self._queue2)
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


