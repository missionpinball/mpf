from typing import Tuple
from unittest.mock import MagicMock

from mpf.core.bcp.bcp_socket_client import decode_command_string, encode_command_string
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockServer, MockQueueSocket


class TestBcp(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']
        self.machine_config_patches['bcp'] = dict()
        self.machine_config_patches['bcp']['connections'] = []

    def get_use_bcp(self):
        return True

    def _mock_loop(self):
        self.mock_server = MockServer(self.clock.loop)
        self.clock.mock_server("127.0.0.1", 5051, self.mock_server)

    def _get_and_decode(self, client) -> Tuple[str, dict]:
        data = client.send_queue.get_nowait()
        return decode_command_string(data[0:-1].decode())

    def _encode_and_send(self, client, cmd, **kwargs):
        client.recv_queue.append((encode_command_string(cmd, **kwargs) + '\n').encode())

    def testConnect(self):
        # check that server was opened
        self.assertTrue(self.mock_server.is_bound)

        # add client
        client = MockQueueSocket(self.loop)
        self.machine.clock.loop.run_until_complete(self.mock_server.add_client(client))
        self.advance_time_and_run()

        # check hello
        self.assertEqual(1, client.send_queue.qsize())
        cmd, kwargs = self._get_and_decode(client)
        self.assertEqual("hello", cmd)

        # test trigger
        self.mock_event("test_event")
        client.recv_queue.append((encode_command_string("trigger", name="test_event") + '\n').encode())
        self.advance_time_and_run()
        self.assertEqual(1, self._events['test_event'])

        # register for event/trigger
        client.recv_queue.append((encode_command_string("register_trigger", event="test_trigger") + '\n').encode())
        self.advance_time_and_run()
        self.assertEqual(0, client.send_queue.qsize())

        # post trigger event
        self.post_event("test_trigger")
        self.advance_time_and_run()
        self.assertEqual(1, client.send_queue.qsize())
        cmd, kwargs = self._get_and_decode(client)
        self.assertEqual("trigger", cmd)
        self.assertEqual("test_trigger", kwargs['name'])

        # send goodbye. machine should continue to run.
        client.close = MagicMock()
        client.recv_queue.append((encode_command_string("goodbye") + '\n').encode())
        self.advance_time_and_run()

        client.close.assert_called_with()

        self.assertFalse(self.machine._done)