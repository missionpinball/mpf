from functools import partial
from queue import Queue
from unittest.mock import MagicMock, patch, call

from mpf.tests.MpfBcpTestCase import MockBcpClient
from mpf.tests.MpfTestCase import MpfTestCase


class TestBcpClient(MockBcpClient):
    def __init__(self, machine, name, bcp):
        super().__init__(machine, name, bcp)
        self.queue = Queue()
        self.exit_on_close = False

    def send(self, bcp_command, kwargs):
        if bcp_command == "reset":
            self.receive_queue.put_nowait(("reset_complete", {}))
        self.queue.put((bcp_command, kwargs))

    def receive(self, bcp_command, callback=None, rawbytes=None, **kwargs):
        if rawbytes:
            kwargs['rawbytes'] = rawbytes
        self.receive_queue.put_nowait((bcp_command, kwargs))

        if callback:
            callback()

class MockMcClock:

    def __init__(self, clock):
        self._clock = clock

    def __getattr__(self, item):
        return getattr(self._clock, item)

    def schedule_once(self, callback, timeout=0):
        self._clock.schedule_once(partial(callback, dt=None), timeout)

    def schedule_interval(self, callback, timeout):
        self._clock.schedule_interval(partial(callback, dt=None), timeout)


class TestBcp(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        self.machine_config_patches['bcp'] = \
            {"connections": {"local_display": {"type": "mpf.tests.test_BcpMc.TestBcpClient"}}}
        self.machine_config_patches['bcp']['servers'] = []

    def get_use_bcp(self):
        return True

    def setUp(self):
        super().setUp()

        client = self.machine.bcp.transport.get_named_client("local_display")
        self.kivy = MagicMock()
        self.kivy.clock.Clock = MockMcClock(self.machine.clock)
        modules = {
            'kivy': self.kivy,
            'kivy.clock': self.kivy.clock,
            'kivy.logger': self.kivy.logger,
        }
        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()

        try:
            from mpfmc.core import bcp_processor
        except ImportError:
            super().tearDown()
            self.skipTest("Cannot import mpfmc.core.bcp_processor")
            return

        self.mc = MagicMock()
        bcp_processor.BcpProcessor._start_socket_thread = MagicMock()
        bcp_mc = bcp_processor.BcpProcessor(self.mc)
        bcp_mc.enabled = True
        bcp_mc.send = client.receive
        bcp_mc._client_connected()
        self.machine_run()
        self.mc.events.post = MagicMock()
        while not client.queue.empty():
            bcp_mc.receive_queue.put(client.queue.get())
        client.queue = bcp_mc.receive_queue
        self.machine_run()

    def tearDown(self):
        self.machine_run()
        self.module_patcher.stop()
        super().tearDown()

    def test_bcp_mpf_and_mpf_mc(self):
        client = self.machine.bcp.transport.get_named_client("local_display")
        self.machine.bcp.interface.add_registered_trigger_event_for_client(client, 'ball_started')
        self.machine.bcp.interface.add_registered_trigger_event_for_client(client, 'ball_ended')
        self.machine.events.post('ball_started', ball=17, player=23)

        self.machine_run()

        self.mc.events.post.assert_has_calls([call("ball_started", ball=17, player=23), ])
        self.mc.events.post.reset_mock()

        self.machine.events.post('ball_ended')
        self.machine_run()
        self.mc.events.post.assert_has_calls([
            call("ball_ended")
        ])
