"""Test event manager."""
from mpf.core.delays import DelayManager
from mpf.core.settings_controller import SettingEntry
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import patch


class TestEventManager(MpfFakeGameTestCase, MpfTestCase):
    def __init__(self, test_map):
        super().__init__(test_map)
        self._handler1_args = tuple()
        self._handler1_kwargs = dict()
        self._handler1_called = 0
        self._handler2_args = tuple()
        self._handler2_kwargs = dict()
        self._handler2_called = 0
        self._handler3_args = tuple()
        self._handler3_kwargs = dict()
        self._handler3_called = 0
        self._handlers_called = list()
        self._handler_returns_false_args = tuple()
        self._handler_returns_false_kwargs = dict()
        self._handler_returns_false_called = 0
        self._relay1_called = 0
        self._relay2_called = 0
        self._relay_callback_args = tuple()
        self._relay_callback_kwargs = dict()
        self._relay_callback_called = 0
        self._callback_args = tuple()
        self._callback_kwargs = dict()
        self._callback_called = 0
        self._queue = None
        self._queue_callback_args = tuple()
        self._queue_callback_kwargs = dict()
        self._queue_callback_called = 0

    def getConfigFile(self):
        return 'test_event_manager.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/event_manager/'

    def event_handler1(self, *args, **kwargs):
        self._handler1_args = args
        self._handler1_kwargs = kwargs
        self._handler1_called += 1
        self._handlers_called.append(self.event_handler1)

    def event_handler2(self, *args, **kwargs):
        self._handler2_args = args
        self._handler2_kwargs = kwargs
        self._handler2_called += 1
        self._handlers_called.append(self.event_handler2)

    def event_handler3(self, *args, **kwargs):
        self._handler3_args = args
        self._handler3_kwargs = kwargs
        self._handler3_called += 1
        self._handlers_called.append(self.event_handler3)

    def event_handler_returns_false(self, *args, **kwargs):
        self._handler_returns_false_args = args
        self._handler_returns_false_kwargs = kwargs
        self._handler_returns_false_called += 1
        self._handlers_called.append(self.event_handler_returns_false)

        return False

    def event_handler_relay1(self, relay_test, **kwargs):
        del kwargs
        self._relay1_called += 1
        self._handlers_called.append(self.event_handler_relay1)

        return {'relay_test': relay_test}

    def event_handler_relay2(self, relay_test, **kwargs):
        del kwargs
        self._relay2_called += 1
        self._handlers_called.append(self.event_handler_relay2)

        return {'relay_test': relay_test - 1}

    def callback(self, *args, **kwargs):
        self._callback_args = args
        self._callback_kwargs = kwargs
        self._callback_called += 1
        self._handlers_called.append(self.callback)

    def relay_callback(self, *args, **kwargs):
        self._relay_callback_args = args
        self._relay_callback_kwargs = kwargs
        self._relay_callback_called += 1
        self._handlers_called.append(self.relay_callback)

    def event_handler_calls_second_event(self, **kwargs):
        del kwargs
        self.machine.events.post('second_event')
        self._handlers_called.append(self.event_handler_calls_second_event)

    def event_handler_add_queue(self, queue, **kwargs):
        del kwargs
        self._handlers_called.append(self.event_handler_add_queue)
        self._queue = queue
        self._queue.wait()

    def event_handler_add_quick_queue(self, queue, **kwargs):
        del kwargs
        self._handlers_called.append(self.event_handler_add_quick_queue)
        self._queue = queue
        self._queue.wait()
        self._queue.clear()

    def event_handler_clear_queue(self, **kwargs):
        del kwargs
        self._handlers_called.append(self.event_handler_clear_queue)
        self._queue.clear()

    def queue_callback(self, *args, **kwargs):
        self._queue_callback_args = args
        self._queue_callback_kwargs = kwargs
        self._queue_callback_called += 1
        self._handlers_called.append(self.queue_callback)

    def test_event(self):
        # tests that a handler responds to a regular event post
        self.machine.events.add_handler('test_event', self.event_handler1)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

    def test_event_double_register(self):
        # tests that a handler responds to a regular event post
        self.machine.events.add_handler('test_event', self.event_handler1)
        self.machine.events.add_handler('test_event', self.event_handler1)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(2, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

    def test_event_with_kwargs(self):
        # test that a kwarg can be passed to a handler which is registered for
        # a regular event post
        self.machine.events.add_handler('test_event', self.event_handler1)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event', test1='test1')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual({'test1': 'test1'}, self._handler1_kwargs)

    def test_event_with_callback(self):
        # test that a callback is called when the event is done
        self.machine.events.add_handler('test_event', self.event_handler1)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event', test1='test1',
                                 callback=self.callback)
        self.advance_time_and_run(1)

        self.assertEqual(1, self._callback_called)

    def test_nested_callbacks(self):
        # tests that an event handlers which posts another event has that event
        # handled before the first event's callback is called

        self.machine.events.add_handler('test_event',
                                        self.event_handler_calls_second_event)
        self.machine.events.add_handler('second_event', self.event_handler1)

        self.advance_time_and_run(1)

        self.machine.events.post('test_event', callback=self.callback)
        self.advance_time_and_run(1)

        self.assertEqual(self._handlers_called[0],
                         self.event_handler_calls_second_event)
        self.assertEqual(self._handlers_called[1],
                         self.event_handler1)
        self.assertEqual(self._handlers_called[2],
                         self.callback)

    def test_event_handler_priorities(self):
        # tests that handler priorities work. The second handler should be
        # called first because it's a higher priority even though it's
        # registered second
        self.machine.events.add_handler('test_event', self.event_handler1,
                                        priority=100)
        self.machine.events.add_handler('test_event', self.event_handler2,
                                        priority=200)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(tuple(), self._handler2_args)
        self.assertEqual(dict(), self._handler2_kwargs)

        self.assertEqual(self._handlers_called[0], self.event_handler2)
        self.assertEqual(self._handlers_called[1], self.event_handler1)

    def test_remove_handler_by_handler(self):
        # tests that a handler can be removed by passing the handler to remove
        self.machine.events.add_handler('test_event', self.event_handler1)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

        self.machine.events.remove_handler(self.event_handler1)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

    def test_remove_handler_by_event(self):
        # tests that a handler can be removed by a handler/event combo, and
        # that only that handler/event combo is removed
        self.machine.events.add_handler('test_event1', self.event_handler1)
        self.machine.events.add_handler('test_event2', self.event_handler1)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event1')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

        # should not remove handler since this is the wrong event
        self.machine.events.remove_handler_by_event('test_event3',
                                                    self.event_handler1)

        self.machine.events.post('test_event1')
        self.advance_time_and_run(1)

        self.assertEqual(2, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

        # remove handler for this event
        self.machine.events.remove_handler_by_event('test_event1',
                                                    self.event_handler1)

        self.machine.events.post('test_event1')
        self.advance_time_and_run(1)

        # results should be the same as above since this handler was removed
        self.assertEqual(2, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

        self.machine.events.post('test_event2')
        self.advance_time_and_run(1)

        # results should be the same as above since this handler was removed
        self.assertEqual(3, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

    def test_remove_handler_by_key(self):
        # tests that a handler responds to a regular event post
        key = self.machine.events.add_handler('test_event',
                                              self.event_handler1)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

        self.machine.events.remove_handler_by_key(key)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

    def test_remove_handlers_by_keys(self):
        # tests that multiple handlers can be removed by an iterable keys list
        keys = list()

        keys.append(self.machine.events.add_handler('test_event1',
                                                    self.event_handler1))
        keys.append(self.machine.events.add_handler('test_event2',
                                                    self.event_handler2))
        self.machine.events.post('test_event1')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

        self.machine.events.post('test_event2')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler2_called)
        self.assertEqual(tuple(), self._handler2_args)
        self.assertEqual(dict(), self._handler2_kwargs)

        self.machine.events.remove_handlers_by_keys(keys)

        # post events again and handlers should not be called again
        self.machine.events.post('test_event1')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)

        self.machine.events.post('test_event2')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler2_called)
        self.assertEqual(tuple(), self._handler2_args)
        self.assertEqual(dict(), self._handler2_kwargs)

    def test_does_event_exist(self):
        self.machine.events.add_handler('test_event', self.event_handler1)

        self.assertEqual(True,
                         self.machine.events.does_event_exist('test_event'))
        self.assertEqual(False,
                         self.machine.events.does_event_exist('test_event1'))

    def test_regular_event_with_false_return(self):
        # tests that regular events process all handlers even if one returns
        # False

        self.machine.events.add_handler('test_event', self.event_handler1,
                                        priority=100)
        self.machine.events.add_handler('test_event',
                                        self.event_handler_returns_false,
                                        priority=200)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(1, self._handler_returns_false_called)

        self.assertEqual(self._handlers_called[0],
                         self.event_handler_returns_false)
        self.assertEqual(self._handlers_called[1], self.event_handler1)

    def test_post_boolean(self):
        # tests that a boolean event works

        self.machine.events.add_handler('test_event', self.event_handler1,
                                        priority=100)
        self.machine.events.add_handler('test_event', self.event_handler2,
                                        priority=200)
        self.advance_time_and_run(1)

        self.machine.events.post_boolean('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(), self._handler1_kwargs)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(tuple(), self._handler2_args)
        self.assertEqual(dict(), self._handler2_kwargs)

        self.assertEqual(self._handlers_called[0], self.event_handler2)
        self.assertEqual(self._handlers_called[1], self.event_handler1)

    def test_boolean_event_with_false_return(self):
        # tests that regular events process all handlers even if one returns
        # False

        self.machine.events.add_handler('test_event', self.event_handler1,
                                        priority=100)
        self.machine.events.add_handler('test_event',
                                        self.event_handler_returns_false,
                                        priority=200)
        self.advance_time_and_run(1)

        self.machine.events.post_boolean('test_event')
        self.advance_time_and_run(1)

        self.assertEqual(0, self._handler1_called)
        self.assertEqual(1, self._handler_returns_false_called)

        self.assertEqual(self._handlers_called[0],
                         self.event_handler_returns_false)

        self.assertEqual(1, len(self._handlers_called))

    def test_relay_event(self):
        # tests that a relay event works by passing a value

        self.machine.events.add_handler('test_event',
                                        self.event_handler_relay1,
                                        priority=200)

        self.advance_time_and_run(1)

        self.machine.events.post_relay('test_event', relay_test=1,
                                       callback=self.relay_callback)
        self.advance_time_and_run(1)

        self.assertEqual(1, self._relay1_called)
        self.assertEqual(1, self._relay_callback_called)

        assert 'relay_test' in self._relay_callback_kwargs
        assert self._relay_callback_kwargs['relay_test'] == 1

    def test_relay_event_handler_changes_value(self):
        # tests that a relay event works by passing a value to a handler that
        # changes that value

        self.machine.events.add_handler('test_event',
                                        self.event_handler_relay1,
                                        priority=200)
        self.machine.events.add_handler('test_event',
                                        self.event_handler_relay2,
                                        priority=100)
        self.advance_time_and_run(1)

        self.machine.events.post_relay('test_event', relay_test=1,
                                       callback=self.relay_callback)
        self.advance_time_and_run(1)

        self.assertEqual(1, self._relay1_called)
        self.assertEqual(1, self._relay2_called)
        self.assertEqual(1, self._relay_callback_called)

        assert 'relay_test' in self._relay_callback_kwargs
        self.assertEqual(self._relay_callback_kwargs['relay_test'], 0)

    def test_queue(self):
        # tests that a queue event works by registering and clearing a queue

        self.machine.events.add_handler('test_event',
                                        self.event_handler_add_queue)

        self.advance_time_and_run(1)

        self.machine.events.post_queue('test_event',
                                       callback=self.queue_callback)
        self.advance_time_and_run(1)

        self.assertEqual(self._handlers_called.count(self.event_handler_add_queue), 1)
        self.assertEqual(self._handlers_called.count(self.queue_callback), 0)
        self.assertEqual(False, self._queue.is_empty())

        self.event_handler_clear_queue()
        self.advance_time_and_run()

        self.assertEqual(self._handlers_called.count(self.queue_callback), 1)
        self.assertEqual(True, self._queue.is_empty())

    def test_queue_event_with_no_queue(self):
        # tests that a queue event works and the callback is called right away
        # if no handlers request a wait

        self.machine.events.add_handler('test_event', self.event_handler1)

        self.advance_time_and_run(1)

        self.machine.events.post_queue('test_event',
                                       callback=self.queue_callback)

        self.advance_time_and_run(1)

        self.assertEqual(self._handlers_called.count(self.event_handler1), 1)
        self.assertEqual(self._handlers_called.count(self.queue_callback), 1)

    def test_queue_event_with_quick_queue_clear(self):
        # tests that a queue event that quickly creates and clears a queue

        self.machine.events.add_handler('test_event',
                                        self.event_handler_add_quick_queue)

        self.advance_time_and_run(1)

        self.machine.events.post_queue('test_event',
                                       callback=self.queue_callback)
        self.advance_time_and_run(1)

        self.assertEqual(self._handlers_called.count(self.event_handler_add_quick_queue), 1)

        self.assertEqual(self._handlers_called.count(self.queue_callback), 1)
        self.assertEqual(True, self._queue.is_empty())

    def test_queue_event_with_no_registered_handlers(self):
        # tests that a queue event callback is called works even if there are
        # not registered handlers for that event

        self.machine.events.post_queue('test_event',
                                       callback=self.queue_callback)
        self.advance_time_and_run(1)

        self.assertEqual(self._handlers_called.count(self.queue_callback), 1)
        self.assertIsNone(self._queue)

    def test_queue_event_with_double_quick_queue_clear(self):
        # tests that a queue event that quickly creates and clears a queue

        self.machine.events.add_handler('test_event',
                                        self.event_handler_add_quick_queue,
                                        priority=1)
        self.machine.events.add_handler('test_event',
                                        self.event_handler_add_quick_queue,
                                        priority=2)

        self.advance_time_and_run(1)

        self.machine.events.post_queue('test_event',
                                       callback=self.queue_callback)
        self.advance_time_and_run(1)

        self.assertEqual(self._handlers_called.count(self.event_handler_add_quick_queue), 2)

        self.assertEqual(self._handlers_called.count(self.queue_callback), 1)
        self.assertEqual(True, self._queue.is_empty())

    def test_event_player(self):
        self.machine.events.add_handler('test_event_player1', self.event_handler1)
        self.machine.events.add_handler('test_event_player2', self.event_handler2)
        self.machine.events.add_handler('test_event_player3', self.event_handler3)
        self.advance_time_and_run(1)

        self.machine.events.post('test_event_player1', test="123")
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(1, self._handler3_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(test="123"), self._handler1_kwargs)
        self.assertEqual(tuple(), self._handler2_args)
        self.assertEqual(dict(priority=0), self._handler2_kwargs)
        self.assertEqual(tuple(), self._handler3_args)
        self.assertEqual(dict(priority=0), self._handler3_kwargs)

    def test_event_player_delay(self):
        self.mock_event('test_event_player2')
        self.mock_event('test_event_player3')

        self.machine.events.post('test_event_player_delayed')
        self.machine_run()
        self.assertEqual(0, self._events['test_event_player2'])
        self.assertEqual(0, self._events['test_event_player3'])
        self.advance_time_and_run(2)
        self.assertEqual(1, self._events['test_event_player2'])
        self.assertEqual(1, self._events['test_event_player3'])

    def test_random_event_player(self):
        self.machine.events.add_handler('test_random_event_player1', self.event_handler1)
        self.machine.events.add_handler('test_random_event_player2', self.event_handler2)
        self.machine.events.add_handler('test_random_event_player3', self.event_handler3)
        self.advance_time_and_run(1)

        with patch('random.randint', return_value=1) as mock_random:
            self.machine.events.post('test_random_event_player1', test="123")
            self.advance_time_and_run(1)
            mock_random.assert_called_once_with(1, 2)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(0, self._handler3_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(test="123"), self._handler1_kwargs)
        self.assertEqual(tuple(), self._handler2_args)
        self.assertEqual(dict(test="123"), self._handler2_kwargs)

        with patch('random.randint', return_value=1) as mock_random:
            self.machine.events.post('test_random_event_player1', test="123")
            self.advance_time_and_run(1)
            mock_random.assert_called_once_with(1, 1)

        self.assertEqual(2, self._handler1_called)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(1, self._handler3_called)
        self.assertEqual(tuple(), self._handler1_args)
        self.assertEqual(dict(test="123"), self._handler1_kwargs)
        self.assertEqual(tuple(), self._handler3_args)
        self.assertEqual(dict(test="123"), self._handler3_kwargs)

    def test_event_player_in_mode(self):
        self.machine.events.add_handler('test_event_player_mode1', self.event_handler1)
        self.machine.events.add_handler('test_event_player_mode2', self.event_handler2)
        self.machine.events.add_handler('test_event_player_mode3', self.event_handler3)
        self.advance_time_and_run(1)

        # mode not loaded. event should not be replayed
        self.machine.events.post('test_event_player_mode1', test="123")
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(0, self._handler2_called)
        self.assertEqual(0, self._handler3_called)

        # start mode
        self.machine.events.post('test_mode_start')
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.mode_controller.is_active("test_mode"))

        # now the event should get replayed
        self.machine.events.post('test_event_player_mode1', test="123")
        self.advance_time_and_run(1)

        self.assertEqual(2, self._handler1_called)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(1, self._handler3_called)

        # stop mode
        self.machine.events.post('test_mode_end')
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.mode_controller.is_active("test_mode"))

        # event should not longer get replayed
        self.machine.events.post('test_event_player_mode1', test="123")
        self.advance_time_and_run(1)

        self.assertEqual(3, self._handler1_called)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(1, self._handler3_called)

    def test_random_event_player_in_mode(self):
        self.machine.events.add_handler('test_random_event_player_mode1', self.event_handler1)
        self.machine.events.add_handler('test_random_event_player_mode2', self.event_handler2)
        self.machine.events.add_handler('test_random_event_player_mode3', self.event_handler3)
        self.advance_time_and_run(1)

        # mode not loaded. event should not be replayed
        self.machine.events.post('test_random_event_player_mode1', test="123")
        self.advance_time_and_run(1)

        self.assertEqual(1, self._handler1_called)
        self.assertEqual(0, self._handler2_called)
        self.assertEqual(0, self._handler3_called)

        # start mode
        self.machine.events.post('test_mode_start')
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.mode_controller.is_active("test_mode"))

        # now the event should get replayed
        with patch('random.randint', return_value=1) as mock_random:
            self.machine.events.post('test_random_event_player_mode1', test="123")
            self.advance_time_and_run(1)
            mock_random.assert_called_once_with(1, 2)

        self.assertEqual(2, self._handler1_called)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(0, self._handler3_called)

        # stop mode
        self.machine.events.post('test_mode_end')
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.mode_controller.is_active("test_mode"))

        # event should not longer get replayed
        self.machine.events.post('test_random_event_player_mode1', test="123")
        self.advance_time_and_run(1)

        self.assertEqual(3, self._handler1_called)
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(0, self._handler3_called)

    def event_block(self, queue, **kwargs):
        del kwargs
        self.queue = queue
        queue.wait()

    def test_random_event_player_in_game_mode(self):
        self.start_game()
        self.machine.events.add_handler('out1', self.event_handler2)
        self.machine.events.add_handler('out2', self.event_handler3)
        self.advance_time_and_run(1)

        # mode not loaded. event should not be replayed
        self.machine.events.post('test_random_event_player_mode2', test="123")
        self.advance_time_and_run(1)

        self.assertEqual(0, self._handler2_called)
        self.assertEqual(0, self._handler3_called)

        # start mode
        self.machine.events.post('game_mode_start')
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.mode_controller.is_active("game_mode"))

        # now the event should get replayed
        with patch('random.randint', return_value=1) as mock_random:
            self.machine.events.post('test_random_event_player_mode2', test="123")
            self.advance_time_and_run(1)
            mock_random.assert_called_once_with(1, 2)

        self.assertEqual(1, self._handler2_called)
        self.assertEqual(0, self._handler3_called)

        # block stop of mode
        self.machine.events.add_handler('mode_game_mode_stopping', self.event_block)

        # stop game
        self.machine.game.stop()
        self.advance_time_and_run()

        # event should still work (and not crash)
        self.machine.events.post('test_random_event_player_mode2', test="123")
        self.machine_run()
        self.assertEqual(1, self._handler2_called)
        self.assertEqual(1, self._handler3_called)

        # when the block ends game should end too
        self.queue.clear()
        self.machine_run()

        # but no longer after clear
        self.machine.events.post('test_random_event_player_mode2', test="123")
        self.machine_run()

        self.advance_time_and_run(1)
        self.assertFalse(self.machine.mode_controller.is_active("game_mode"))

        self.assertEqual(1, self._handler2_called)
        self.assertEqual(1, self._handler3_called)

    def delay1_cb(self, **kwargs):
        del kwargs
        self.machine.events.post("event1")

    def event1_cb(self, **kwargs):
        del kwargs
        self.delay.add(ms=100, callback=self.delay2_cb)

    def delay2_cb(self, **kwargs):
        del kwargs
        self.machine.events.post("event2")

    def event2_cb(self, **kwargs):
        del kwargs
        self.delay.add(ms=100, callback=self.delay3_cb)

    def delay3_cb(self, **kwargs):
        del kwargs
        self.machine.events.post("event3")

    def event3_cb(self, **kwargs):
        del kwargs
        self.correct = True

    def test_event_in_delay(self):
        self.machine.events.add_handler('event1', self.event1_cb)
        self.machine.events.add_handler('event2', self.event2_cb)
        self.machine.events.add_handler('event3', self.event3_cb)
        self.correct = False
        self.delay = DelayManager(self.machine.delayRegistry)

        self.machine.events.post("event1")
        self.advance_time_and_run(1)

        self.assertTrue(self.correct)

    def delay_first(self):
        self.called = True
        self.delay.remove("second")

    def delay_second(self):
        if not self.called:
            raise AssertionError("first has not been called")

        raise AssertionError("this should never be called")

    def test_delay_order(self):
        self.called = False
        self.delay = DelayManager(self.machine.delayRegistry)

        self.delay.add(ms=6001, name="second", callback=self.delay_second)
        self.delay.add(ms=6000, name="first", callback=self.delay_first)

        self.advance_time_and_run(10)

    def delay_zero_ms(self, start):
        self.delay.add(ms=0, name="second", callback=self.delay_zero_ms_next_frame, start=start)

    def delay_zero_ms_next_frame(self, start):
        self.assertLessEqual(self.machine.clock.get_time(), start)

    def test_zero_ms_delay(self):
        self.called = False
        self.delay = DelayManager(self.machine.delayRegistry)

        self.delay.add(ms=0, name="first", callback=self.delay_zero_ms, start=self.machine.clock.get_time())
        self.advance_time_and_run(10)

    def _handler(self, **kwargs):
        del kwargs
        self._called += 1

    def test_handler_with_condition(self):
        self._called = 0
        self.machine.events.add_handler("test{param > 1 and a == True}", self._handler)

        self.post_event("test")
        self.assertEqual(0, self._called)

        self.post_event_with_params("test", param=3, a=False)
        self.assertEqual(0, self._called)

        self.post_event_with_params("test", param=3, a=True)
        self.assertEqual(1, self._called)

    def test_handler_with_settings_condition_invalid_setting(self):
        self._called = 0
        self.machine.events.add_handler("test{settings.test == True}", self._handler)

        # invalid setting
        with self.assertRaises(AssertionError):
            self.post_event("test")
            self.assertEqual(0, self._called)

        # reset exception
        self._exception = None

    def test_handler_with_settings_condition(self):
        self._called = 0
        self.machine.events.add_handler("test{settings.test == True}", self._handler)


        self.machine.settings._settings = {}
        self.machine.settings.add_setting(SettingEntry("test", "Test", 1, "test", "a",
                                                       {False: "A (default)", True: "B"}))

        # setting false
        self.post_event("test")
        self.assertEqual(0, self._called)

        self.machine.settings.set_setting_value("test", True)

        # settings true
        self.post_event("test")
        self.assertEqual(1, self._called)

    def test_weighted(self):
        self.mock_event("out3")
        self.mock_event("out4")

        self.post_event("test_mode_start")
        self.advance_time_and_run()

        with patch('random.randint', return_value=1) as mock_random:
            self.machine.events.post('test_random_event_player_weighted')
            self.advance_time_and_run(1)
            mock_random.assert_called_once_with(1, 1001)

        self.assertEventCalled("out3")
        self.assertEventNotCalled("out4")

        self.mock_event("out3")
        self.mock_event("out4")

        with patch('random.randint', return_value=2) as mock_random:
            self.machine.events.post('test_random_event_player_weighted')
            self.advance_time_and_run(1)
            mock_random.assert_called_once_with(1, 1001)

        self.assertEventNotCalled("out3")
        self.assertEventCalled("out4")

        self.mock_event("out3")
        self.mock_event("out4")

        with patch('random.randint', return_value=500) as mock_random:
            self.machine.events.post('test_random_event_player_weighted')
            self.advance_time_and_run(1)
            mock_random.assert_called_once_with(1, 1001)

        self.assertEventNotCalled("out3")
        self.assertEventCalled("out4")
