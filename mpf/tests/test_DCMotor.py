from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestDCMotor(MpfTestCase):

    def get_config_file(self):
        return "config.yaml"

    def get_machine_path(self):
        return 'tests/machine_files/dc_motor/'

    def test_dc_motor_device_allocation(self):
        motor = self.machine.dc_motors['test_motor_1']
        self.assertIsNotNone(motor)
        self.assertEqual(motor.platform, self.machine.default_platform)
        self.assertEqual("VirtualDCMotor.1", repr(motor.hw_motor))

    def test_control_events_parsing_and_execution(self):
        motor = self.machine.dc_motors['test_motor_1']
        mock_hw = MagicMock()
        motor.hw_motor = mock_hw
        self.machine.events.post('trigger_motor_1_pulse_event')
        self.advance_time_and_run(0.1)
        mock_hw.pulse.assert_called_once_with(1.5, 0.75)

        self.machine.events.post('trigger_motor_1_reverse_pulse_event')
        self.advance_time_and_run(0.1)
        mock_hw.reverse_pulse.assert_called_once_with(2.5, 0.5)

    def test_stop_action_cleanup(self):
        motor = self.machine.dc_motors['test_motor_1']
        mock_hw = MagicMock()
        motor.hw_motor = mock_hw
        self.machine.events.post('kill_motor_1_motion_event')
        self.advance_time_and_run(0.1)
        mock_hw.stop.assert_called_once()
