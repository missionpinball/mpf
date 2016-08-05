from mpf.tests.MpfTestCase import MpfTestCase


class TestBcpInterface(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type":  "mpf.tests.MpfTestCase.MockBcpClient"}}}
        self.machine_config_patches['bcp']['servers'] = []

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/bcp/'

    def test_receive_register_trigger(self):
        client = self.machine.bcp.transport.get_named_client("local_display")
        client.receive_queue.put_nowait(('register_trigger', {'event': 'test_event'}))
        self.advance_time_and_run()

        self.assertIn('test_event', self.machine.bcp.transport._handlers)

    def test_receive_switch(self):
        client = self.machine.bcp.transport.get_named_client("local_display")

        # should not crash
        client.receive_queue.put_nowait(('switch', {'name': 'invalid_switch', 'state': 1}))
        self.advance_time_and_run()

        # initially inactive
        self.assertFalse(self.machine.switch_controller.is_active('s_test'))

        # receive active
        client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': 1}))
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active('s_test'))

        # receive active
        client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': 1}))
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active('s_test'))

        # and inactive again
        client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': 0}))
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active('s_test'))

        # invert
        client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': -1}))
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active('s_test'))

        # invert
        client.receive_queue.put_nowait(('switch', {'name': 's_test', 'state': -1}))
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active('s_test'))
