"""Test the bcp interface."""
import asyncio
from unittest import mock

from mpf.core.events import RegisteredHandler
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase


class CallHandler:
    def __repr__(self):
        return "handler"

    def __call__(self, *args, **kwargs):
        pass


class TestBcpInterface(MpfBcpTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
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
        self._bcp_external_client.reset_and_return_queue()
        self._bcp_external_client.send('monitor_start', {'category': 'events'})
        self.advance_time_and_run()

        self.machine.events.post("test1")
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ('monitored_event', dict(event_name='test1', event_type=None,
                                     event_callback=None, event_kwargs={},
                                     registered_handlers=[])),
            queue)

        self.machine.events.post("test2")
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ('monitored_event', dict(event_name='test2', event_type=None,
                                     event_callback=None, event_kwargs={},
                                     registered_handlers=[RegisteredHandler(callback='handler', priority=1, kwargs={}, key='abc', condition=None, blocking_facility=None)])),
            queue)

        self.machine.events.post("test3", callback=handler)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ('monitored_event', dict(registered_handlers=[], event_name='test3',
                                     event_type=None, event_callback=handler,
                                     event_kwargs={})),
            queue)

        # Now stop the event monitoring
        self._bcp_external_client.reset_and_return_queue()
        self._bcp_external_client.send('monitor_stop', {'category': 'events'})
        self.advance_time_and_run()

        # Event should not be sent via BCP
        self.machine.events.post("test1")
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

    def test_device_monitor(self):
        self.hit_switch_and_run("s_test", .1)
        self.release_switch_and_run("s_test2", .1)
        self._bcp_external_client.reset_and_return_queue()

        # register monitor
        self._bcp_external_client.send('monitor_start', {'category': 'devices'})
        self.advance_time_and_run()

        # initial states
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 1, 'recycle_jitter_count': 0},
                        "changes": False}), queue)
        self.assertNotIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 0, 'recycle_jitter_count': 0},
                        "changes": False}), queue)
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test2",
                        "state": {'state': 0, 'recycle_jitter_count': 0},
                        "changes": False}), queue)
        self.assertNotIn(
            ("device", {"type": "switch",
                        "name": "s_test2",
                        "state": {'state': 1, 'recycle_jitter_count': 0},
                        "changes": False}), queue)

        # change switch
        self.release_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 0, 'recycle_jitter_count': 0},
                        "changes": ('state', 1, 0)}),
            queue)

        # nothing should happen
        self.release_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

        # change again
        self.hit_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("device", {"type": "switch",
                        "name": "s_test",
                        "state": {'state': 1, 'recycle_jitter_count': 0},
                        "changes": ('state', 0, 1)}),
            queue)

        # Now stop the monitor
        self._bcp_external_client.send('monitor_stop', {'category': 'devices'})
        self.advance_time_and_run()
        self._bcp_external_client.reset_and_return_queue()

        # Switch hit should not be in BCP queue
        self.hit_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

    def test_switch_monitor(self):
        self._bcp_external_client.reset_and_return_queue()

        # register monitor
        self._bcp_external_client.send('monitor_start', {'category': 'switches'})
        self.advance_time_and_run()
        self.hit_switch_and_run("s_test", .1)
        self.hit_and_release_switch("s_test2")
        self.advance_time_and_run()

        # initial states
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("switch", {"name": "s_test",
                        "state": 1}), queue)
        self.assertNotIn(
            ("switch", {"name": "s_test",
                        "state": 0}), queue)
        self.assertIn(
            ("switch", {"name": "s_test2",
                        "state": 0}), queue)
        self.assertIn(
            ("switch", {"name": "s_test2",
                        "state": 1}), queue)

        # change switch
        self.release_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("switch", {"name": "s_test",
                        "state": 0}),
            queue)

        # nothing should happen
        self.release_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

        # change again
        self.hit_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("switch", {"name": "s_test",
                        "state": 1}),
            queue)

        # Stop switch monitor
        self._bcp_client.send_queue = asyncio.Queue()
        self._bcp_client.receive_queue.put_nowait(('monitor_stop', {'category': 'switches'}))
        self.advance_time_and_run()

        # Hit switch should not be in BCP queue
        self.hit_switch_and_run("s_test", .1)
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

    def test_mode_monitor(self):
        self.assertIn('mode1', self.machine.modes)
        self.assertIn('mode2', self.machine.modes)

        self._bcp_external_client.reset_and_return_queue()

        # register monitor
        self._bcp_external_client.send('monitor_start', {'category': 'modes'})
        self.advance_time_and_run()

        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertEqual(1, len(queue))
        self.assertListEqual(
            [
                ("mode_list", {"running_modes": [("attract", 10)]})
            ],
            queue)

        # start mode 1
        self.post_event("start_mode1")
        self.advance_time_and_run()

        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertListEqual(
            [
                ("mode_start", {"priority": 200, "name": "mode1"}),
                ("mode_list", {"running_modes": [("mode1", 200), ("attract", 10)]})
            ],
            queue)

        # start mode 2
        self.post_event("start_mode2")
        self.advance_time_and_run()

        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertListEqual(
            [
                ("mode_start", {"priority": 100, "name": "mode2"}),
                ("mode_list", {"running_modes": [("mode1", 200), ("mode2", 100), ("attract", 10)]})
            ],
            queue)

        # stop mode 1
        self.post_event("stop_mode1")
        self.advance_time_and_run()

        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertListEqual(
            [
                ("mode_stop", {"name": "mode1"}),
                ("mode_list", {"running_modes": [("mode2", 100), ("attract", 10)]})
            ],
            queue)

        # Stop monitoring modes
        self._bcp_external_client.send('monitor_stop', {'category': 'modes'})
        self.advance_time_and_run()

        # start mode 1 again
        self.post_event("start_mode1")
        self.advance_time_and_run()

        # The BCP queue should be empty
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

    def test_machine_vars_monitor(self):
        # register monitor
        self._bcp_external_client.send('monitor_start', {'category': 'machine_vars'})
        self.advance_time_and_run()
        self._bcp_external_client.reset_and_return_queue()

        # Create a new machine variable
        self.machine.variables.set_machine_var("test_var", "testing")
        queue = self._bcp_external_client.reset_and_return_queue()

        self.assertIn(
            ("machine_variable", {"value": "testing",
                                  "name": "test_var",
                                  "change": True,
                                  "prev_value": None}),
            queue)

        self.machine.variables.set_machine_var("test_var", "2nd")
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("machine_variable", {"value": "2nd",
                                  "name": "test_var",
                                  "change": True,
                                  "prev_value": "testing"}),
            queue)

        # Now stop monitoring machine variables
        self._bcp_external_client.send('monitor_stop', {'category': 'machine_vars'})
        self.advance_time_and_run()
        self._bcp_external_client.reset_and_return_queue()
        self.machine.variables.set_machine_var("test_var", "3rd")

        # The BCP queue should be empty
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

    def test_player_vars_monitor(self):
        # register monitor
        self._bcp_external_client.send('monitor_start', {'category': 'player_vars'})
        self.advance_time_and_run()

        # Setup and start game (player variables are stored in game)
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(2, self.machine.ball_devices["bd_trough"].balls)

        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()

        self.assertEqual(3, self.machine.modes["game"].balls_per_game)
        self.assertEqual(1, self.machine.game.num_players)
        self._bcp_external_client.reset_and_return_queue()

        # Create a new player variable
        self.machine.game.player.test_var = "testing"
        queue = self._bcp_external_client.reset_and_return_queue()

        self.assertIn(
            ("player_variable", {"player_num": 1,
                                 "value": "testing",
                                 "prev_value": 0,
                                 "name": "test_var",
                                 "change": True}),
            queue)

        self.machine.game.player.test_var = "2nd"
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(
            ("player_variable", {"player_num": 1,
                                 "value": "2nd",
                                 "prev_value": "testing",
                                 "name": "test_var",
                                 "change": True}),
            queue)

        # Now stop monitoring machine variables
        self._bcp_external_client.send('monitor_stop', {'category': 'player_vars'})
        self.advance_time_and_run()
        self._bcp_external_client.reset_and_return_queue()
        self.machine.variables.set_machine_var("test_var", "3rd")

        # The BCP queue should be empty
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

    def test_receive_switch(self):
        # should not crash
        self._bcp_external_client.send('switch', {'name': 'invalid_switch', 'state': 1})
        self.advance_time_and_run()

        # initially inactive
        self.assertSwitchState("s_test", 0)

        # receive active
        self._bcp_external_client.send('switch', {'name': 's_test', 'state': 1})
        self.advance_time_and_run()
        self.assertSwitchState("s_test", 1)

        # receive active
        self._bcp_external_client.send('switch', {'name': 's_test', 'state': 1})
        self.advance_time_and_run()
        self.assertSwitchState("s_test", 1)

        # and inactive again
        self._bcp_external_client.send('switch', {'name': 's_test', 'state': 0})
        self.advance_time_and_run()
        self.assertSwitchState("s_test", 0)

        # invert
        self._bcp_external_client.send('switch', {'name': 's_test', 'state': -1})
        self.advance_time_and_run()
        self.assertSwitchState("s_test", 1)

        # invert
        self._bcp_external_client.send('switch', {'name': 's_test', 'state': -1})
        self.advance_time_and_run()
        self.assertSwitchState("s_test", 0)

    def test_double_reset_complete(self):
        # Test when a BCP server sends reset_complete twice (was causing MPF to crash)
        self._bcp_external_client.send('reset_complete', {})
        self.advance_time_and_run()
        self._bcp_external_client.send('reset_complete', {})
        self.advance_time_and_run()

    def test_receive_monitor_status_request(self):
        # Test when a BCP server sends monitor start and stop commands for status_request messages
        client = self.machine.bcp.transport.get_named_client("local_display")
        self.assertNotIn('_status_request', self.machine.bcp.transport._handlers)
        self.assertFalse(self.machine.bcp.transport.get_transports_for_handler('_status_request'))

        client.receive_queue.put_nowait(('monitor_start', {'category': 'status_request'}))
        self.advance_time_and_run()
        self.assertIn('_status_request', self.machine.bcp.transport._handlers)
        self.assertTrue(self.machine.bcp.transport.get_transports_for_handler('_status_request'))

        client.receive_queue.put_nowait(('monitor_stop', {'category': 'status_request'}))
        self.advance_time_and_run()
        self.assertFalse(self.machine.bcp.transport.get_transports_for_handler('_status_request'))

    def test_triggers(self):
        # Test triggers and the trigger player which is used to send trigger messages from MPF over BCP
        client = self.machine.bcp.transport.get_named_client("local_display")

        # First send trigger before BCP server has registered for it (should not be sent)
        self.machine.bcp.interface.bcp_trigger("trigger_test")
        self.advance_time_and_run()
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)

        client.receive_queue.put_nowait(('register_trigger', {'event': 'trigger_test'}))
        self.advance_time_and_run()
        self.machine.bcp.interface.bcp_trigger("trigger_test")
        self.advance_time_and_run()
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(("trigger", {"name": "trigger_test"}), queue)

        # Now test the event_player to send a registered trigger
        self.post_event("send_test_trigger")
        self.advance_time_and_run()
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertIn(("trigger", {"priority": 0, "name": "trigger_test"}), queue)

        # Unregister the trigger and re-test (should not be sent)
        client.receive_queue.put_nowait(('remove_trigger', {'event': 'trigger_test'}))
        self.advance_time_and_run()
        self.post_event("send_test_trigger")
        self.advance_time_and_run()
        queue = self._bcp_external_client.reset_and_return_queue()
        self.assertFalse(queue)
