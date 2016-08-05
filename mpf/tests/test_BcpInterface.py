"""Test the bcp interface."""
from mpf.tests.MpfBcpTestCase import MpfBcpTestCase


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

    def test_switch_monitor(self):
        self.hit_switch_and_run("s_test", .1)
        self.release_switch_and_run("s_test2", .1)
        self._bcp_client.send_queue.clear()

        # register monitor
        self._bcp_client.receive_queue.put_nowait(('monitor_devices', {}))
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
