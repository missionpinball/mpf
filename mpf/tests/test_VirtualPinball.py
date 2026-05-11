import asyncio
from typing import Tuple

from mpf.core.bcp.bcp_socket_client import decode_command_string, encode_command_string

from mpf.tests.loop import MockServer, MockQueueSocket

from mpf.tests.MpfTestCase import MpfTestCase


class TestVirtualPinball(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        # remove config patch which disables bcp
        del self.machine_config_patches['bcp']
        self.machine_config_patches['bcp'] = dict()
        self.machine_config_patches['bcp']['connections'] = []

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/virtual_pinball/'

    def get_use_bcp(self):
        return True

    def _mock_loop(self):
        self.mock_server = MockServer(self.clock.loop)
        self.clock.mock_server("127.0.0.1", 5051, self.mock_server)

    @staticmethod
    async def _get_and_decode(client) -> Tuple[str, dict]:
        data = await client.send_queue.get()
        return decode_command_string(data[0:-1].decode())

    def _encode_and_send(self, client, cmd, **kwargs):
        client.recv_queue.append((encode_command_string(cmd, **kwargs) + '\n').encode())

    def test_virtual_pinball(self):
        # connect a client
        client = MockQueueSocket(self.loop)
        self.loop.run_until_complete(self.mock_server.add_client(client))

        # check hello
        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("hello", cmd)

        self._encode_and_send(client, "monitor_start", category="switches")
        self._encode_and_send(client, "monitor_start", category="drivers")
        self._encode_and_send(client, "monitor_start", category="devices")

        self.advance_time_and_run()
        client.send_queue = asyncio.Queue()

        self.machine.lights["test_light1"].on()

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("device", cmd)
        self.assertEqual("test_light1", args['name'])
        self.assertEqual("light", args['type'])
        self.assertEqual({'color': [255, 255, 255]}, args['state'])

        self.machine.coils["c_test"].pulse()
        self.advance_time_and_run()

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("driver_event", cmd)
        self.assertEqual("pulse", args['action'])
        self.assertEqual("c_test", args['name'])
        self.assertEqual("0-0", args['number'])
        self.assertEqual(23, args['pulse_ms'])
        self.assertEqual(1.0, args['pulse_power'])

        self.machine.coils["c_test_allow_enable"].enable()
        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("driver_event", cmd)
        self.assertEqual("enable", args['action'])
        self.assertEqual("c_test_allow_enable", args['name'])
        self.assertEqual("0-1", args['number'])
        self.assertEqual(23, args['pulse_ms'])
        self.assertEqual(1.0, args['pulse_power'])
        self.assertEqual(1.0, args['hold_power'])

        self.machine.coils["c_test_allow_enable"].disable()
        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("driver_event", cmd)
        self.assertEqual("disable", args['action'])
        self.assertEqual("c_test_allow_enable", args['name'])
        self.assertEqual("0-1", args['number'])

        self.machine.flippers["f_test_single"].enable()
        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("device", cmd)
        self.assertEqual("f_test_single", args['name'])
        self.assertEqual("flipper", args['type'])
        self.assertEqual({"enabled": True}, args['state'])

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("driver_event", cmd)
        self.assertEqual({'enable_switch_invert': False,
                          'coil_name': 'c_flipper_main',
                          'coil_pulse_power': 1.0,
                          'coil_hold_power': 'HoldSettings(power=0.375, duration=None)',
                          'enable_switch_name': 's_flipper',
                          'enable_switch_number': '0-3',
                          'coil_pulse_ms': 10,
                          'coil_number': '0-3',
                          'action': 'pulse_on_hit_and_enable_and_release',
                          'coil_recycle': False,
                          'enable_switch_debounce': False}, args)

        self.machine.flippers["f_test_single"].disable()
        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("driver_event", cmd)
        self.assertEqual({'coil_number': '0-3',
                          'enable_switch_invert': False,
                          'action': 'remove',
                          'enable_switch_number': '0-3'}, args)

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("device", cmd)
        self.assertEqual("f_test_single", args['name'])
        self.assertEqual("flipper", args['type'])
        self.assertEqual({"enabled": False}, args['state'])

        self.assertSwitchState("s_test_nc", 0)

        self._encode_and_send(client, "switch", name="s_test_nc", state=1)
        self.advance_time_and_run()
        self.assertSwitchState("s_test_nc", 1)

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("device", cmd)
        self.assertEqual("switch", args['type'])
        self.assertEqual("s_test_nc", args['name'])
        self.assertEqual(["state", 0, 1], args['changes'])
        self.assertEqual({'state': 1, 'recycle_jitter_count': 0}, args['state'])

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("switch", cmd)
        self.assertEqual("s_test_nc", args['name'])
        self.assertEqual(1, args['state'])

        # Prove that virtual supports delayed kickbacks
        self.post_event("enable_kickback_test")

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        # Yes you do it twice for some reason (they are the same)
        self.assertEqual("device", cmd)
        self.assertEqual("kickback", args['type'])
        self.assertEqual("kickback_test", args['name'])
        self.assertEqual(["enabled", False, True], args['changes'])
        self.assertEqual({"enabled": True}, args['state'])

        cmd, args = self.loop.run_until_complete(self._get_and_decode(client))
        self.assertEqual("driver_event", cmd)
        self.assertEqual(args, {
                'action': 'delayed_pulse_on_hit',
                'enable_switch_number': '0-9',
                'enable_switch_name': 's_kickback',
                'enable_switch_invert': False,
                'enable_switch_debounce': False,
                'coil_number': '1-13',
                'coil_name': 'c_kickback',
                'coil_pulse_power': 1.0,
                'coil_pulse_ms': 20,
                'coil_hold_power': 0,
                'coil_recycle': True,
                'delay_ms': 10
            })

