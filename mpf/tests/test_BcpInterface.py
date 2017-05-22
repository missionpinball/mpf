"""Test the bcp interface."""
from unittest import mock

from mpf.core.events import RegisteredHandler
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase


class CallHandler:
    def __repr__(self):
        return "handler"

    def __call__(self, *args, **kwargs):
        pass


class TestBcpInterface(MpfBcpTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/bcp/'

    def test_receive_register_trigger(self):
        client = self.machine.bcp.transport.get_named_client("local_display")
        client.receive_queue.put_nowait(('register_trigger', {'event': 'test_event'}))
        self.advance_time_and_run()

        self.assertIn('test_event', self.machine.bcp.transport._handlers)

    def _cb(self, **kwargs):
        pass

    def test_monitor_events(self):

        handler = CallHandler()
        with mock.patch("uuid.uuid4", return_value="abc"):
            self.machine.events.add_handler("test2", handler)
        self._bcp_client.send_queue.clear()
        self._bcp_client.receive_queue.put_nowait(('monitor_start', {'category': 'events'}))
        self.advance_time_and_run()

        self.machine.events.post("test1")
        self.assertIn(
            ('monitored_event', dict(event_name='test1', event_type=None,
                                     event_callback=None, event_kwargs={},
                                     registered_handlers=[])),
            self._bcp_client.send_queue)

        self._bcp_client.send_queue.clear()
        self.machine.events.post("test2")

        self.assertIn(
            ('monitored_event', dict(event_name='test2', event_type=None,
                                     event_callback=None, event_kwargs={},
                                     registered_handlers=[RegisteredHandler(callback='handler', priority=1, kwargs={}, key='abc', condition=None)])),
            self._bcp_client.send_queue)

        self._bcp_client.send_queue.clear()
        self.machine.events.post("test3", callback=handler)
        self.assertIn(
            ('monitored_event', dict(registered_handlers=[], event_name='test3',
                                     event_type=None, event_callback=handler,
                                     event_kwargs={})),
            self._bcp_client.send_queue)

        # Now stop the event monitoring
        self._bcp_client.send_queue.clear()
        self._bcp_client.receive_queue.put_nowait(('monitor_stop', {'category': 'events'}))
        self.advance_time_and_run()

        # Event should not be sent via BCP
        self.machine.events.post("test1")
        self.assertFalse(self._bcp_client.send_queue)

    def test_device_monitor(self):
        self.hit_switch_and_run("s_test", .1)
        self.release_switch_and_run("s_test2", .1)
        self._bcp_client.send_queue.clear()

        # register monitor
        self._bcp_client.receive_queue.put_nowait(('monitor_start', {'category': 'devices'}))
        self.advance_time_and_run()

        # initial states
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 1, 'recycle_jitter_count': 0},
                        "changes": False}), self._bcp_client.send_queue)
        self.assertNotIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 0, 'recycle_jitter_count': 0},
                        "changes": False}), self._bcp_client.send_queue)
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test2",
                        "state": {'state': 0, 'recycle_jitter_count': 0},
                        "changes": False}), self._bcp_client.send_queue)
        self.assertNotIn(
            ("device", {"type": "switch",
                        "name": "s_test2",
                        "state": {'state': 1, 'recycle_jitter_count': 0},
                        "changes": False}), self._bcp_client.send_queue)
        self._bcp_client.send_queue.clear()

        # change switch
        self.release_switch_and_run("s_test", .1)
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 0, 'recycle_jitter_count': 0},
                        "changes": ('state', 1, 0)}),
            self._bcp_client.send_queue)
        self._bcp_client.send_queue.clear()

        # nothing should happen
        self.release_switch_and_run("s_test", .1)
        self.assertFalse(self._bcp_client.send_queue)

        # change again
        self.hit_switch_and_run("s_test", .1)
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 1, 'recycle_jitter_count': 0},
                        "changes": ('state', 0, 1)}),
            self._bcp_client.send_queue)

        # Now stop the monitor
        self._bcp_client.receive_queue.put_nowait(('monitor_stop', {'category': 'devices'}))
        self.advance_time_and_run()
        self._bcp_client.send_queue.clear()

        # Switch hit should not be in BCP queue
        self.hit_switch_and_run("s_test", .1)
        self.assertFalse(self._bcp_client.send_queue)

    def test_switch_monitor(self):
        self._bcp_client.send_queue.clear()

        # register monitor
        self._bcp_client.receive_queue.put_nowait(('monitor_start', {'category': 'switches'}))
        self.advance_time_and_run()
        self.hit_switch_and_run("s_test", .1)
        self.hit_and_release_switch("s_test2")
        self.advance_time_and_run()

        # initial states
        self.assertIn(
            ("switch", {"name": "s_test",
                        "state": 1}), self._bcp_client.send_queue)
        self.assertNotIn(
            ("switch", {"name": "s_test",
                        "state": 0}), self._bcp_client.send_queue)
        self.assertIn(
            ("switch", {"name": "s_test2",
                        "state": 0}), self._bcp_client.send_queue)
        self.assertIn(
            ("switch", {"name": "s_test2",
                        "state": 1}), self._bcp_client.send_queue)
        self._bcp_client.send_queue.clear()

        # change switch
        self.release_switch_and_run("s_test", .1)
        self.assertIn(
            ("switch", {"name": "s_test",
                        "state": 0}),
            self._bcp_client.send_queue)
        self._bcp_client.send_queue.clear()

        # nothing should happen
        self.release_switch_and_run("s_test", .1)
        self.assertFalse(self._bcp_client.send_queue)

        # change again
        self.hit_switch_and_run("s_test", .1)
        self.assertIn(
            ("switch", {"name": "s_test",
                        "state": 1}),
            self._bcp_client.send_queue)

        # Stop switch monitor
        self._bcp_client.send_queue.clear()
        self._bcp_client.receive_queue.put_nowait(('monitor_stop', {'category': 'switches'}))
        self.advance_time_and_run()

        # Hit switch should not be in BCP queue
        self.hit_switch_and_run("s_test", .1)
        self.assertFalse(self._bcp_client.send_queue)

    def test_mode_monitor(self):
        self.assertIn('mode1', self.machine.modes)
        self.assertIn('mode2', self.machine.modes)

        self._bcp_client.send_queue.clear()

        # register monitor
        self._bcp_client.receive_queue.put_nowait(('monitor_start', {'category': 'modes'}))
        self.advance_time_and_run()
        self.assertFalse(self._bcp_client.send_queue)

        # start mode 1
        self.machine.modes['mode1'].config['mode']['game_mode'] = False
        self.machine.modes['mode1'].start(mode_priority=200)
        self.machine.modes['mode1'].active = True

        self.assertIn(
            ("mode_start", {"priority": 200, "name": "mode1"}),
            self._bcp_client.send_queue)

        self._bcp_client.send_queue.clear()

        # start mode 2
        self.machine.modes['mode2'].config['mode']['game_mode'] = False
        self.machine.modes['mode2'].start(mode_priority=100)
        self.machine.modes['mode2'].active = True

        # stop mode 1
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()

        self.assertIn(
            ("mode_start", {"priority": 100, "name": "mode2"}),
            self._bcp_client.send_queue)
        self.assertIn(
            ("mode_stop", {"name": "mode1"}),
            self._bcp_client.send_queue)

        self._bcp_client.send_queue.clear()

        # Stop monitoring modes
        self._bcp_client.receive_queue.put_nowait(('monitor_stop', {'category': 'modes'}))
        self.advance_time_and_run()

        # start mode 1 again
        self.machine.modes['mode1'].config['mode']['game_mode'] = False
        self.machine.modes['mode1'].start(mode_priority=200)
        self.machine.modes['mode1'].active = True

        # The BCP queue should be empty
        self.assertFalse(self._bcp_client.send_queue)

    def test_machine_vars_monitor(self):
        # register monitor
        self._bcp_client.receive_queue.put_nowait(('monitor_start', {'category': 'machine_vars'}))
        self.advance_time_and_run()
        self._bcp_client.send_queue.clear()

        # Create a new machine variable
        self.machine.create_machine_var("test_var", "testing")

        self.assertIn(
            ("machine_variable", {"value": "testing",
                                  "name": "test_var",
                                  "change": False,
                                  "prev_value": "testing"}),
            self._bcp_client.send_queue)
        self._bcp_client.send_queue.clear()

        self.machine.set_machine_var("test_var", "2nd")
        self.assertIn(
            ("machine_variable", {"value": "2nd",
                                  "name": "test_var",
                                  "change": True,
                                  "prev_value": "testing"}),
            self._bcp_client.send_queue)

        # Now stop monitoring machine variables
        self._bcp_client.receive_queue.put_nowait(('monitor_stop', {'category': 'machine_vars'}))
        self.advance_time_and_run()
        self._bcp_client.send_queue.clear()
        self.machine.set_machine_var("test_var", "3rd")

        # The BCP queue should be empty
        self.assertFalse(self._bcp_client.send_queue)

    def test_player_vars_monitor(self):
        # register monitor
        self._bcp_client.receive_queue.put_nowait(('monitor_start', {'category': 'player_vars'}))
        self.advance_time_and_run()

        # Setup and start game (player variables are stored in game)
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices.bd_trough.balls)

        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()

        self.assertEqual(3, self.machine.modes.game.balls_per_game)
        self.assertEqual(1, self.machine.game.num_players)
        self._bcp_client.send_queue.clear()

        # Create a new player variable
        self.machine.game.player.test_var = "testing"

        self.assertIn(
            ("player_variable", {"player_num": 1,
                                 "value": "testing",
                                 "prev_value": 0,
                                 "name": "test_var",
                                 "change": True}),
            self._bcp_client.send_queue)
        self._bcp_client.send_queue.clear()

        self.machine.game.player.test_var = "2nd"
        self.assertIn(
            ("player_variable", {"player_num": 1,
                                 "value": "2nd",
                                 "prev_value": "testing",
                                 "name": "test_var",
                                 "change": True}),
            self._bcp_client.send_queue)

        # Now stop monitoring machine variables
        self._bcp_client.receive_queue.put_nowait(('monitor_stop', {'category': 'player_vars'}))
        self.advance_time_and_run()
        self._bcp_client.send_queue.clear()
        self.machine.set_machine_var("test_var", "3rd")

        # The BCP queue should be empty
        self.assertFalse(self._bcp_client.send_queue)

    def test_receive_switch(self):
        # should not crash
        self._bcp_client.receive_queue.put_nowait(('switch', {'name': 'invalid_switch', 'state': 1}))
        self.advance_time_and_run()

        # initially inactive
        self.assertFalse(self.machine.switch_controller.is_active('s_test'))

        # receive active
        self._bcp_client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': 1}))
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active('s_test'))

        # receive active
        self._bcp_client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': 1}))
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active('s_test'))

        # and inactive again
        self._bcp_client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': 0}))
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active('s_test'))

        # invert
        self._bcp_client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': -1}))
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active('s_test'))

        # invert
        self._bcp_client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': -1}))
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active('s_test'))

    def test_double_reset_complete(self):
        # Test when a BCP server sends reset_complete twice (was causing MPF to crash)
        self._bcp_client.receive_queue.put_nowait(('reset_complete', {}))
        self.advance_time_and_run()
        self._bcp_client.receive_queue.put_nowait(('reset_complete', {}))
        self.advance_time_and_run()
