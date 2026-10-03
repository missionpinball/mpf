"""Real-asyncio regression tests for PKONE/EX2 startup and stream handling."""
import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from mpf.platforms.pkone.pkone_serial_communicator import PKONESerialCommunicator
from mpf.platforms.pkone.pkone import PKONEHardwarePlatform
from mpf.platforms.pkone.pkone_switch import PKONESwitchNumber


class TestPKONEStartup(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.platform = SimpleNamespace(
            machine=SimpleNamespace(variables=Mock(), switch_controller=Mock(), stop=Mock()),
            config={'debug': False}, log=logging.getLogger('pkone-test'), debug_log=Mock(),
            pkone_extensions={}, pkone_lightshows={}, hw_switch_data={})
        self.platform.register_extension_board = lambda b: self.platform.pkone_extensions.update({b.addr: b})
        self.platform.register_lightshow_board = lambda b: self.platform.pkone_lightshows.update({b.addr: b})
        self.platform.process_received_message = self.dispatch
        self.connection = PKONESerialCommunicator(self.platform, 'simulated-ex2', 115200)
        self.connection.reader = asyncio.StreamReader()
        self.responses = {b'PCNE': b'PCNF20H20E', b'PRSE': b'PRSE',
                          b'PCB0E': b'PCB0XF20H20PYE', b'PCB1E': b'PCB1LF10H1RGBWE',
                          b'PSA0E': b'PSA0' + b'01' * 17 + b'0E'}
        self.responses.update({f'PCB{i}E'.encode(): f'PCB{i}NE'.encode() for i in range(2, 8)})
        self.connection.writer = Mock()
        self.connection.writer.write.side_effect = self.reply

    def reply(self, command):
        response = self.responses.get(command)
        if response:
            self.connection.reader.feed_data(response)

    def dispatch(self, message):
        payload = message[3:].removesuffix('E')
        if message.startswith('PSA'):
            PKONEHardwarePlatform.receive_all_switches(self.platform, payload)
        elif message.startswith('PSW'):
            PKONEHardwarePlatform.receive_switch(self.platform, payload)

    async def test_ex2_integrated_io_and_lightshow_startup(self):
        await self.connection._identify_connection()
        self.assertEqual([0], list(self.platform.pkone_extensions))
        self.assertTrue(self.platform.pkone_lightshows[1].rgbw_firmware)
        self.assertEqual(35, len(self.platform.hw_switch_data))
        self.assertEqual(1, self.platform.hw_switch_data[PKONESwitchNumber(0, 2)])
        self.assertIs(self.connection, self.platform.controller_connection)
        self.platform.machine.variables.set_machine_var.assert_any_call('pkone_hardware', 'PKONE Controller (rev 20)')

    async def test_bad_board_reply_fails_clearly(self):
        for reply in (b'PCB0F20H20YE', b'PCB0QF20H20E', b'PCB9XF20H20E'):
            with self.subTest(reply=reply):
                self.responses[b'PCB0E'] = reply
                with self.assertRaisesRegex(AssertionError, 'Invalid PKONE board reply'):
                    await self.connection.query_pkone_boards()

    async def test_wrong_board_address_is_rejected(self):
        self.responses[b'PCB0E'] = b'PCB1XF20H20E'
        with self.assertRaisesRegex(AssertionError, 'address mismatch'):
            await self.connection.query_pkone_boards()

    async def test_reset_error_and_unexpected_ack(self):
        for reply in (b'PXX1001E', b'PRSQE'):
            with self.subTest(reply=reply):
                self.responses[b'PRSE'] = reply
                with self.assertRaises(AssertionError):
                    await self.connection.reset_controller()

    async def test_silent_and_noisy_device_have_bounded_wait(self):
        with self.assertRaisesRegex(AssertionError, 'Timed out'):
            await self.connection._wait_for_response('PRS', 'resetting', timeout=.01)
        self.connection.reader.feed_data(b'PWDE' * 2000)
        with self.assertRaisesRegex(AssertionError, 'Timed out'):
            await self.connection._wait_for_response('PRS', 'resetting', timeout=.01)

    async def test_disconnect_and_non_ascii(self):
        self.connection.reader.feed_data(b'\xffE')
        with self.assertRaisesRegex(AssertionError, 'Non-ASCII'):
            await self.connection._read_with_timeout(.01)
        self.connection.reader.feed_eof()
        with self.assertRaisesRegex(AssertionError, 'disconnected'):
            await self.connection._read_with_timeout(.01)

    async def test_bad_snapshot_does_not_partially_update_states(self):
        await self.connection.query_pkone_boards()
        for reply in (b'PXX1001E', b'PSA0E', b'PSA1'+b'0'*35+b'E', b'PSA0'+b'2'*35+b'E'):
            self.responses[b'PSA0E'] = reply
            with self.subTest(reply=reply), self.assertRaises(AssertionError):
                await self.connection.read_all_switches()
            self.assertEqual({}, self.platform.hw_switch_data)

    async def test_fragmented_and_coalesced_runtime_events(self):
        await self.connection._identify_connection()
        self.connection._parse_msg(b'PSW001')
        self.platform.machine.switch_controller.process_switch_by_num.assert_not_called()
        self.connection._parse_msg(b'1EPSW0020E')
        self.assertEqual(2, self.platform.machine.switch_controller.process_switch_by_num.call_count)
        self.assertEqual(1, self.platform.hw_switch_data[PKONESwitchNumber(0, 1)])
        self.assertEqual(0, self.platform.hw_switch_data[PKONESwitchNumber(0, 2)])

    async def test_invalid_switch_event(self):
        await self.connection._identify_connection()
        for payload in ('0001', '0361', '1011', '0012', '', '00111'):
            with self.subTest(payload=payload), self.assertRaises(AssertionError):
                PKONEHardwarePlatform.receive_switch(self.platform, payload)
        self.platform.machine.switch_controller.process_switch_by_num.assert_not_called()

    async def test_unterminated_stream_is_bounded(self):
        with self.assertRaisesRegex(AssertionError, 'exceeds'):
            self.connection._parse_msg(b'x' * 1025)
        self.assertEqual(b'', self.connection.received_msg)

    async def test_watchdog_report_stops_machine(self):
        PKONEHardwarePlatform.receive_watchdog_timeout(self.platform, '')
        self.platform.machine.stop.assert_called_once()

    async def test_switch_source_profile_and_peripheral_reset_replies(self):
        self.responses[b'PRSE'] = b'PRS1LEPRS2SEPRSNE'
        self.responses[b'PCB2E'] = b'PCB2SF20H20I40C00PNE'
        self.responses[b'PSA2E'] = b'PSA2' + b'0' * 39 + b'1E'
        await self.connection._identify_connection()
        board = self.platform.pkone_extensions[2]
        self.assertEqual((40, 0, 0), (board.switch_count, board.coil_count, board.servo_count))
        self.assertEqual(75, len(self.platform.hw_switch_data))
        self.assertEqual(1, self.platform.hw_switch_data[PKONESwitchNumber(2, 40)])
        self.connection._parse_msg(b'PSW2400E')
        self.assertEqual(0, self.platform.hw_switch_data[PKONESwitchNumber(2, 40)])

    async def test_unknown_switch_profile_rejected(self):
        for reply in (b'PCB2SF20H20I50C03PNE', b'PCB2SF20H20I40C02PNE'):
            self.responses[b'PCB2E'] = reply
            with self.subTest(reply=reply), self.assertRaises(AssertionError):
                await self.connection.query_pkone_boards()

    async def test_mixed_lightshow_configures_each_port(self):
        self.responses[b'PCB1E'] = b'PCB1LF14H112MIXE'
        self.platform.config['lightshow_groups'] = {'1-1': 'rgb', '1-2': 'rgbw'}
        self.responses.update({b'PLT113E': b'PLT113E', b'PLT124E': b'PLT124E'})
        await self.connection._identify_connection()
        board = self.platform.pkone_lightshows[1]
        self.assertTrue(board.mixed_firmware)
        self.assertEqual(3, board.channels_for_group(1))
        self.assertEqual(4, board.channels_for_group(2))
        for group in (0, 3, 9):
            with self.assertRaises(AssertionError):
                board.channels_for_group(group)

    async def test_mixed_wrong_ack_does_not_enable_port(self):
        self.responses[b'PCB1E'] = b'PCB1LF14H112MIXE'
        self.platform.config['lightshow_groups'] = {'1-1': 'rgb'}
        self.responses[b'PLT113E'] = b'PLT114E'
        with self.assertRaisesRegex(AssertionError, 'acknowledgement'):
            await self.connection._identify_connection()
        self.assertEqual({}, self.platform.pkone_lightshows[1].group_types)

    async def test_invalid_port_configuration_rejected_before_writes(self):
        await self.connection.query_pkone_boards()
        for config in ({'1-9': 'rgb'}, {'1-1': 'unknown'}, {'3-1': 'rgb'}, {'1-1': 'rgb'}):
            self.platform.config['lightshow_groups'] = config
            self.connection.writer.reset_mock()
            with self.subTest(config=config), self.assertRaises(AssertionError):
                await self.connection.configure_lightshow_groups()
            self.connection.writer.write.assert_not_called()

    async def test_legacy_matching_type_sends_no_new_command(self):
        await self.connection.query_pkone_boards()
        self.platform.config['lightshow_groups'] = {'1-1': 'rgbw'}
        self.connection.writer.reset_mock()
        await self.connection.configure_lightshow_groups()
        self.connection.writer.write.assert_not_called()

    async def test_mixed_board_emits_rgb_and_rgbw_batches(self):
        self.responses[b'PCB1E'] = b'PCB1LF14H112MIXE'
        self.platform.config['lightshow_groups'] = {'1-1': 'rgb', '1-2': 'rgbw'}
        self.responses.update({b'PLT113E': b'PLT113E', b'PLT124E': b'PLT124E'})
        await self.connection._identify_connection()
        self.platform.controller_connection = Mock()
        for group, count, opcode in ((1, 3, 'PLB'), (2, 4, 'PWB')):
            channels = PKONEHardwarePlatform.parse_light_number_to_channels(self.platform, f'1-{group}-64', 'led')
            self.assertEqual(count, len(channels))
            self.assertEqual(f'1-{group}-{count*63}', channels[0]['number'])
            batch = [(SimpleNamespace(board_address_id=1, group=group, index=i), 1.0, 0) for i in range(count)]
            await PKONEHardwarePlatform._send_multiple_light_update(self.platform, batch)
            self.platform.controller_connection.send.assert_called_with(f'{opcode}1{group}01010000' + '255'*count)
