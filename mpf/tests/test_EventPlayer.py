"""Test event player."""
from collections import namedtuple

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
        self.post_event("play_multiple_args2")
        self.assertEqual({"a": "b", "c": "d", "priority": 0}, self._last_event_kwargs['event1'])

        self.mock_event("event1")
        self.mock_event("event2")
        self.mock_event("event3")
        self.machine.shows['test_event_show'].play(loops=0)
        self.advance_time_and_run()
        self.assertEqual(1, self._events['event1'])
        self.assertEqual(1, self._events['event2'])
        self.assertEqual(1, self._events['event3'])

    def test_condition_and_priority(self):
        self.mock_event("condition_ok")
        self.mock_event("condition_ok2")
        self.mock_event("priority_ok")
        self.post_event("test_conditional")
        self.assertEventNotCalled("condition_ok")
        self.assertEventNotCalled("condition_ok2")
        self.assertEventCalled("priority_ok")

        arg_obj = namedtuple("Arg", ["abc"])
        arg = arg_obj(1)

        self.post_event_with_params("test_conditional", arg=arg)
        self.assertEventCalled("condition_ok")
        self.assertEventCalled("condition_ok2")

    def test_handler_condition(self):
        # test neither condition passing
        self.mock_event("event_always")
        self.mock_event("event_if_modeactive")
        self.mock_event("event_if_modestopping")

        self.assertEqual(0, self._events["event_always"])
        self.assertEqual(0, self._events["event_if_modeactive"])
        self.assertEqual(0, self._events["event_if_modestopping"])
        self.post_event("test_conditional_handlers")
        self.assertEqual(1, self._events["event_always"])
        self.assertEqual(0, self._events["event_if_modeactive"])
        self.assertEqual(0, self._events["event_if_modestopping"])

        # test one condition passing
        self.mock_event("event_always")
        self.mock_event("event_if_modeactive")
        self.mock_event("event_if_modestopping")

        self.machine.modes.mode1.start()
        self.advance_time_and_run()
        self.assertEqual(0, self._events["event_always"])
        self.assertEqual(0, self._events["event_if_modeactive"])
        self.assertEqual(0, self._events["event_if_modestopping"])
        self.post_event("test_conditional_handlers")
        self.assertEqual(1, self._events["event_always"])
        self.assertEqual(1, self._events["event_if_modeactive"])
        self.assertEqual(0, self._events["event_if_modestopping"])

        # test both conditions passing
        self.mock_event("event_always")
        self.mock_event("event_if_modeactive")
        self.mock_event("event_if_modestopping")

        self.machine.modes.mode1.stop()
        self.assertEqual(0, self._events["event_always"])
        self.assertEqual(0, self._events["event_if_modeactive"])
        self.assertEqual(0, self._events["event_if_modestopping"])
        self.post_event("test_conditional_handlers")
        self.assertEqual(1, self._events["event_always"])
        self.assertEqual(1, self._events["event_if_modeactive"])
        self.assertEqual(1, self._events["event_if_modestopping"])

    def test_event_time_delays(self):
        self.mock_event('td1')
        self.mock_event('td2')

        self.post_event('test_time_delay1')
        self.advance_time_and_run(1)
        self.assertEventNotCalled('td1')
        self.advance_time_and_run(1)
        self.assertEventCalled('td1')

        self.post_event('test_time_delay2')
        self.advance_time_and_run(1)
        self.assertEventNotCalled('td2')
        self.advance_time_and_run(1)
        self.assertEventCalled('td2')

    def test_mode_condition(self):
        self.mock_event('mode1_active')
        self.mock_event('mode1_not_active')

        self.assertFalse(self.machine.modes.mode1.active)

        self.post_event('test_conditional_mode')

        self.assertEventNotCalled('mode1_active')
        self.assertEventCalled('mode1_not_active')

        self.mock_event('mode1_active')
        self.mock_event('mode1_not_active')

        self.machine.modes.mode1.start()
        self.advance_time_and_run()

        self.post_event('test_conditional_mode')
        self.assertTrue(self.machine.modes.mode1.active)

        self.assertEventCalled('mode1_active')
        self.assertEventNotCalled('mode1_not_active')

    def test_event_placeholder(self):
        self.mock_event('my_event_None_123')
        self.mock_event('my_event_hello_world_123')

        self.post_event("play_placeholder_event")
        self.assertEventCalled("my_event_None_123")
        self.mock_event('my_event_None_123')
        self.assertEventNotCalled("my_event_hello_world_123")

        self.machine.set_machine_var("test", "hello_world")
        self.post_event("play_placeholder_event")
        self.assertEventNotCalled("my_event_None_123")
        self.assertEventCalled("my_event_hello_world_123")
