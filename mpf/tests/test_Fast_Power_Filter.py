# mpf.tests.test_Fast_Power_Filter

from mpf.platforms.fast.fast_power_filter import FastPowerFilterBoard
from mpf.tests.MpfTestCase import expect_startup_error
from mpf.tests.test_Fast import TestFastBase

GOOD_IV = 'IV:3328,3393,0CDA,0CDC,0CD3,0CA4'  # 48.32, 48.72, 12.14, 12.15, 12.11, 11.94 V


class TestFastPowerFilterBase(TestFastBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['exp']

    def get_config_file(self):
        return 'power_filter.yaml'

    def create_connections(self):
        super().create_connections()
        # a Neuron firmware that passes the min_fw check, so MPF is not stopped during the test
        self.exp_cpu.id_overrides['48'] = 'ID:EXP FP-EXP-2000  0.48'

    def create_expected_commands(self):
        # Neuron's local LED breakout (480) is cleared and configured on boot
        self.serial_connections['exp'].expected_commands = {
            'RA@480:000000': '',
            'ER@480:0,0,00,20': 'ER:P',
            'ER@480:1,0,20,20': 'ER:P',
            'ER@480:2,0,40,20': 'ER:P',
            'ER@480:3,0,60,20': 'ER:P',
        }

    @property
    def board(self) -> FastPowerFilterBoard:
        return self.machine.hardware_platforms['fast'].exp_breakout_boards['481']

    @property
    def mock_board(self):
        return self.exp_cpu.power_filters['481']

    def var(self, name):
        return self.machine.variables.get_machine_var(name)

    def assert_passthrough_closed(self):
        """Every EB: was followed by a NUL byte, except for a session that is running right now."""
        running = 1 if self.board.communicator.passthrough_active else 0
        self.assertEqual(self.exp_cpu.msg_history.count('EB:01') - running, self.exp_cpu.msg_history.count('\x00'))
        if not running:
            self.assertIsNone(self.exp_cpu.passthrough)


class TestFastPowerFilter(TestFastPowerFilterBase):

    """FP-PWR-0007 on breakout 1 of the Neuron, answering normally."""

    def test_readings(self):
        self.advance_time_and_run(3)

        self.assertIsInstance(self.board, FastPowerFilterBoard)
        self.assertEqual('0.10', self.board.firmware_version)
        self.assertEqual(0x3F, self.var('fast_power_filter_fuses'))
        self.assertEqual('ok', self.var('fast_power_filter_status'))
        self.assertEqual(48.3, self.var('fast_power_filter_hv1_voltage'))
        self.assertEqual(48.7, self.var('fast_power_filter_hv2_voltage'))
        self.assertEqual(12.1, self.var('fast_power_filter_cabinet_voltage'))
        self.assertEqual(11.9, self.var('fast_power_filter_cpu_voltage'))
        for channel in ('hv1', 'hv2', 'cabinet', 'backbox', 'playfield', 'cpu'):
            self.assertEqual(1, self.var(f'fast_power_filter_{channel}_fuse_ok'))
        self.assertAlmostEqual(48.32, self.board.voltages['hv1'])

        # only the two read commands ever go to the breakout, and the passthrough is always closed
        self.assertGreaterEqual(self.exp_cpu.passthrough_sessions, 3)
        self.assertEqual({('481', 'IF:'), ('481', 'IV:')}, set(self.exp_cpu.passthrough_log))
        self.assert_passthrough_closed()

        info = self.machine.hardware_platforms['fast'].get_info_string()
        self.assertIn('Power Filter Board: FP-PWR-0007 @481, Firmware: 0.10, Status: ok, Fuses: 3F', info)
        self.assertIn('hv1 48.32V', info)

    def test_led_updates_never_inside_passthrough(self):
        process_msg = self.exp_cpu.process_msg
        self.exp_cpu.process_msg = lambda cmd: process_msg(cmd) or cmd.startswith('RD@')  # accept LED frames

        for i in range(30):
            self.machine.lights['led1'].color('ff0000' if i % 2 else '0000ff')
            self.advance_time_and_run(.1)

        self.assertIn('RD@480:', ''.join(self.exp_cpu.msg_history))
        self.assertEqual({'IF:', 'IV:'}, {cmd for _, cmd in self.exp_cpu.passthrough_log})

    def test_fuse_blown_and_restored(self):
        self.mock_event('fast_power_filter_fuse_blown')
        self.mock_event('fast_power_filter_fuse_restored')
        self.advance_time_and_run(3)
        self.assertEventNotCalled('fast_power_filter_fuse_blown')

        self.mock_board['IF:'] = 'IF:3B'  # bit 2 = cabinet
        self.advance_time_and_run(3)
        self.assertEventCalledWith('fast_power_filter_fuse_blown', channel='cabinet', fuses=0x3B)
        self.assertEqual(0, self.var('fast_power_filter_cabinet_fuse_ok'))
        self.assertEqual(1, self.var('fast_power_filter_hv1_fuse_ok'))
        self.assertEqual('fault', self.var('fast_power_filter_status'))
        self.assertEventNotCalled('fast_power_filter_fuse_restored')

        self.mock_board['IF:'] = 'IF:3F'
        self.advance_time_and_run(3)
        self.assertEventCalledWith('fast_power_filter_fuse_restored', channel='cabinet', fuses=0x3F)
        self.assertEqual(1, self.var('fast_power_filter_cabinet_fuse_ok'))
        self.assertEqual('ok', self.var('fast_power_filter_status'))

    def test_single_bad_reading_is_ignored(self):
        self.advance_time_and_run(3)
        self.mock_event('fast_power_filter_fuse_blown')
        self.mock_event('fast_power_filter_voltage_fault')

        self.board._process_readings({'IF:': '00', 'IV:': '0000,0000,0000,0000,0000,0000'})
        self.board._process_readings({'IF:': '3F', 'IV:': GOOD_IV[3:]})
        self.board._process_readings({'IF:': '3F', 'IV:': GOOD_IV[3:]})
        self.advance_time_and_run(.1)

        self.assertEventNotCalled('fast_power_filter_fuse_blown')
        self.assertEventNotCalled('fast_power_filter_voltage_fault')
        self.assertEqual('ok', self.var('fast_power_filter_status'))

    def test_voltage_fault(self):
        self.mock_event('fast_power_filter_voltage_fault')
        self.mock_event('fast_power_filter_voltage_ok')
        self.advance_time_and_run(3)

        self.mock_board['IV:'] = 'IV:2A00,3393,0CDA,0CDC,0CD3,0CA4'  # hv1 = 39.67 V
        self.advance_time_and_run(3)
        self.assertEventCalledWith('fast_power_filter_voltage_fault', channel='hv1', voltage=39.67,
                                   low=43.2, high=52.8)
        self.assertEqual(39.7, self.var('fast_power_filter_hv1_voltage'))
        self.assertEqual('fault', self.var('fast_power_filter_status'))
        self.assertEqual(1, self.var('fast_power_filter_hv1_fuse_ok'))

        self.mock_board['IV:'] = GOOD_IV
        self.advance_time_and_run(3)
        self.assertEventCalledWith('fast_power_filter_voltage_ok', channel='hv1', voltage=48.32,
                                   low=43.2, high=52.8)
        self.assertEqual('ok', self.var('fast_power_filter_status'))

    def test_noise_does_not_move_the_voltage_variable(self):
        """ADC noise of about 0.1 V must not post a machine_var_ event on every poll."""
        self.advance_time_and_run(3)
        self.assertEqual(48.3, self.var('fast_power_filter_hv1_voltage'))
        self.mock_event('machine_var_fast_power_filter_hv1_voltage')

        for counts in ('333D', '3311', '333D', '3311'):  # 48.40 and 48.24 V, one per poll
            self.mock_board['IV:'] = 'IV:' + counts + GOOD_IV[7:]
            self.advance_time_and_run(2)
        self.assertEventNotCalled('machine_var_fast_power_filter_hv1_voltage')
        self.assertEqual(48.3, self.var('fast_power_filter_hv1_voltage'))
        self.assertAlmostEqual(48.24, self.board.voltages['hv1'])  # the raw reading is always current

        self.mock_board['IV:'] = 'IV:32EB' + GOOD_IV[7:]  # 48.10 V
        self.advance_time_and_run(2)
        self.assertEventCalled('machine_var_fast_power_filter_hv1_voltage', times=1)
        self.assertEqual(48.1, self.var('fast_power_filter_hv1_voltage'))

    def test_board_stops_responding(self):
        self.mock_event('fast_power_filter_not_responding')
        self.mock_event('fast_power_filter_responding')
        self.advance_time_and_run(3)

        self.exp_cpu.power_filters['481'] = {'ID': 'ID:PWR FP-PWR-0432  0.10'}  # silent inside the passthrough
        self.advance_time_and_run(4)
        self.assertEventCalled('fast_power_filter_not_responding', times=1)
        self.assertEqual('not_responding', self.var('fast_power_filter_status'))
        # the passthrough is left even though nothing answered
        self.assert_passthrough_closed()

        self.exp_cpu.power_filters['481'] = {'ID': 'ID:PWR FP-PWR-0432  0.10', 'IF:': 'IF:3F', 'IV:': GOOD_IV}
        self.advance_time_and_run(15)  # after three failures, only every 10th poll is sent
        self.assertEventCalled('fast_power_filter_responding', times=1)
        self.assertEqual('ok', self.var('fast_power_filter_status'))

    def test_passthrough_not_accepted(self):
        # No EB:P: the NUL + CR still goes out (harmless without an open passthrough), nothing else is sent
        self.mock_event('fast_power_filter_not_responding')
        self.advance_time_and_run(3)
        self.exp_cpu.eb_reply = None
        self.advance_time_and_run(4)
        self.assertEventCalled('fast_power_filter_not_responding', times=1)
        self.assertEqual(self.exp_cpu.msg_history.count('EB:01'), self.exp_cpu.msg_history.count('\x00'))
        self.assertNotIn('IF:', self.exp_cpu.msg_history[-3:])

    def test_backoff_while_not_responding(self):
        self.advance_time_and_run(3)
        self.exp_cpu.power_filters['481'] = {'ID': 'ID:PWR FP-PWR-0432  0.10'}
        self.advance_time_and_run(5)
        sessions = self.exp_cpu.passthrough_sessions
        self.advance_time_and_run(9)
        self.assertLessEqual(self.exp_cpu.passthrough_sessions - sessions, 1)

    def test_cancelled_session_leaves_passthrough(self):
        # On shutdown the writer task is cancelled, possibly in the middle of a session.
        self.advance_time_and_run(3)
        self.exp_cpu.power_filters['481'] = {'ID': 'ID:PWR FP-PWR-0432  0.10'}  # silent, so the session waits
        comm = self.board.communicator
        for _ in range(300):
            if comm.passthrough_active:
                break
            self.advance_time_and_run(.01)
        self.assertTrue(comm.passthrough_active)
        self.assertEqual('481', self.exp_cpu.passthrough)

        comm.write_task.cancel()
        self.advance_time_and_run(.01)
        self.assertFalse(comm.passthrough_active)
        self.assertEqual('\x00', self.exp_cpu.msg_history[-1])
        self.assertIsNone(self.exp_cpu.passthrough)


class TestFastPowerFilterMissing(TestFastPowerFilterBase):

    """FP-PWR-0007 configured, but ID@481: answers ID:F (cable not connected)."""

    def create_connections(self):
        super().create_connections()
        self.exp_cpu.power_filters['481'] = None

    def test_mpf_runs_without_board(self):
        self.advance_time_and_run(5)
        self.assertFalse(self.machine.is_shutting_down)
        self.assertFalse(self.board.hw_verified)
        self.assertEqual('not_responding', self.var('fast_power_filter_status'))
        self.assertEqual(0, self.exp_cpu.passthrough_sessions)
        self.assertIsNone(self.var('fast_power_filter_fuses'))


class TestFastPowerFilterUnknownFirmware(TestFastPowerFilterBase):

    """A newer firmware may report IV: in volts, so MPF only reads the fuses."""

    def create_connections(self):
        super().create_connections()
        self.exp_cpu.power_filters['481']['ID'] = 'ID:PWR FP-PWR-0432  0.11'

    def test_only_fuses_are_read(self):
        self.advance_time_and_run(3)
        self.assertEqual(0x3F, self.var('fast_power_filter_fuses'))
        self.assertEqual('ok', self.var('fast_power_filter_status'))
        self.assertIsNone(self.var('fast_power_filter_hv1_voltage'))
        self.assertEqual({'IF:'}, {cmd for _, cmd in self.exp_cpu.passthrough_log})


class TestFastPowerFilterOldFirmware(TestFastPowerFilterBase):

    """Firmware below min_fw: MPF keeps running without the board."""

    def create_connections(self):
        super().create_connections()
        self.exp_cpu.power_filters['481']['ID'] = 'ID:PWR FP-PWR-0432  0.09'

    def test_board_is_ignored(self):
        self.advance_time_and_run(3)
        self.assertFalse(self.machine.is_shutting_down)
        self.assertEqual('not_responding', self.var('fast_power_filter_status'))
        self.assertEqual(0, self.exp_cpu.passthrough_sessions)


class TestFastPowerFilterWrongBoard(TestFastPowerFilterBase):

    """The power filter board only works on the Neuron's FP-EXP-2000."""

    def get_config_file(self):
        return 'power_filter_wrong_board.yaml'

    def create_expected_commands(self):
        pass

    @expect_startup_error()
    def test_config_error(self):
        self.assertIsNotNone(self.startup_error)
        self.assertIn('can only be connected to FP-EXP-2000', str(self.startup_error))
