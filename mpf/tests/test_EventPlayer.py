"""Test event player."""
from mpf.tests.MpfTestCase import MpfTestCase


class TestEventPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'test_event_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/event_players/'

    def test_load_and_play(self):
        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.post_event("play_express_single")
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(0, self._events['event2'])
        self.assertEqual(0, self._events['event3'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.post_event("play_express_multiple")
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(1, self._events['event2'])
        self.assertEqual(0, self._events['event3'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.post_event("play_single_list")
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(0, self._events['event2'])
        self.assertEqual(0, self._events['event3'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.post_event("play_single_string")
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(0, self._events['event2'])
        self.assertEqual(0, self._events['event3'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.post_event("play_multiple_list")
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(1, self._events['event2'])
        self.assertEqual(1, self._events['event3'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.post_event("play_multiple_string")
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(1, self._events['event2'])
        self.assertEqual(1, self._events['event3'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.post_event("play_multiple_args")
        self.assertEqual(1, self._events['event1'])
        self.assertEqual({"a": "b", "priority": 0}, self._last_event_kwargs['event1'])
        self.assertEqual(1, self._events['event2'])
        self.assertEqual({"priority": 0}, self._last_event_kwargs['event2'])
        self.assertEqual(1, self._events['event3'])
        self.assertEqual({"a": 1, "b": 2, "priority": 0}, self._last_event_kwargs['event3'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.machine.shows['test_event_show'].play(loops=0)
        self.advance_time_and_run()
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(1, self._events['event2'])
        self.assertEqual(1, self._events['event3'])
