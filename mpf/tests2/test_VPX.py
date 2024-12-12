import asyncio
from typing import Tuple

from mpf.core.bcp.bcp_socket_client import decode_command_string, encode_command_string

from mpf.tests.loop import MockServer, MockQueueSocket

from mpf.tests.MpfTestCase import MpfTestCase


class TestVPX(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']
        self.machine_config_patches['bcp'] = dict()
        self.machine_config_patches['bcp']['connections'] = []
        self.client = None

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/vpx/'

    def get_use_bcp(self):
        return True

    def get_platform(self):
        return False

    def _mock_loop(self):
        self.mock_server = MockServer(self.clock.loop)
        self.clock.mock_server("127.0.0.1", 5051, self.mock_server)

    def _early_machine_init(self, machine):
        org_init = machine._run_init_phases
        async def _init_hook():
            machine.events.add_async_handler("init_phase_4", self._send_init)
            await org_init()
        machine._run_init_phases = _init_hook

    async def _send_init(self, **kwargs):
        self.client = MockQueueSocket(self.loop)
        await self.mock_server.add_client(self.client)
        # check hello
        cmd, args = await self._get_and_decode(self.client)
        self.assertEqual("hello", cmd)

        self._encode_and_send("start")

    @staticmethod
    async def _get_and_decode(client) -> Tuple[str, dict]:
        data = await client.send_queue.get()
        return decode_command_string(data[0:-1].decode())

    def read_vpx_response_from_bcp(self):
        cmd, args = self.loop.run_until_complete(self._get_and_decode(self.client))
        self.assertEqual(cmd, "vpcom_bridge_response")
        self.assertNotIn("error", args, "Error: {}".format(args.get("error")))
        return args.get("result")

    def _encode_and_send(self, cmd, **kwargs):
        self.client.recv_queue.append((encode_command_string("vpcom_bridge", subcommand=cmd, **kwargs) + '\n').encode())

    def test_vpx(self):
        self.advance_time_and_run()
        self.client.send_queue = asyncio.Queue()

        self._encode_and_send("changed_lamps")
        self._encode_and_send("changed_solenoids")

        self.read_vpx_response_from_bcp()
        self.read_vpx_response_from_bcp()

        self.machine.lights["test_light1"].on()
        self.advance_time_and_run(.1)
        self._encode_and_send("changed_lamps")
        result = self.read_vpx_response_from_bcp()
        self.assertEqual(result, [['0', True]])

        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run(.001)

        self._encode_and_send("changed_solenoids")
        result = self.read_vpx_response_from_bcp()
        self.assertEqual(result, [['2', True]])
        self.advance_time_and_run(.1)
        self._encode_and_send("changed_solenoids")
        result = self.read_vpx_response_from_bcp()
        self.assertEqual(result, [['2', False]])

        self.machine.coils["c_test"].enable()
        self.advance_time_and_run(.001)

        self._encode_and_send("changed_solenoids")
        result = self.read_vpx_response_from_bcp()
        self.assertEqual(result, [['2', True]])

        self.machine.coils["c_test"].disable()
        self.advance_time_and_run(.001)

        self._encode_and_send("changed_solenoids")
        result = self.read_vpx_response_from_bcp()
        self.assertEqual(result, [['2', False]])

        self.machine.flippers["f_test"].enable()
        self.advance_time_and_run(.001)
        self._encode_and_send("get_hardwarerules")
        result = self.read_vpx_response_from_bcp()
        self.assertEqual(result, [['3', '1', True]])

        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self.advance_time_and_run(.001)
        self._encode_and_send("get_hardwarerules")
        result = self.read_vpx_response_from_bcp()
        self.assertCountEqual(result, [['3', '1', True], ['0', '0', False]])

        self.machine.flippers["f_test"].disable()
        self.advance_time_and_run(.001)
        self._encode_and_send("get_hardwarerules")
        result = self.read_vpx_response_from_bcp()
        self.assertEqual(result, [['0', '0', False]])

        self.assertSwitchState("s_test", False)
        self._encode_and_send("set_switch", number=6, value=1)
        self.advance_time_and_run(.1)
        self.read_vpx_response_from_bcp()
        self.assertSwitchState("s_test", True)
        self._encode_and_send("set_switch", number=6, value=0)
        self.advance_time_and_run(.1)
        self.read_vpx_response_from_bcp()
        self.assertSwitchState("s_test", False)
