from unittest.mock import MagicMock, patch
import unittest
from mpf.platforms.fast.communicators.net_neuron import FastNetNeuronCommunicator

class TestFastSoftPowerDownUnit(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_neuron_soft_power_button_scenarios(self, mock_popen):
        """Verify the full behavioral matrix of the soft power button logic in isolation."""
        mock_platform = MagicMock()
        mock_platform.machine = MagicMock()
        mock_platform.machine.clock.get_time.return_value = 1000.0  # Base clock time

        # Mock configuration lookups matching how net_neuron.py accesses them
        mock_platform.config = {
            'net': {
                'soft_power_hold_ms': 2500,
                'soft_power_powerdown_delay': 4000
            }
        }
        mock_platform.soft_power_hold_ms = 2500
        mock_platform.soft_power_held_time = None

        mock_communicator_config = {'debug': False, 'io_loop': {}, 'console_log': 'none', 'file_log': 'none'}
        communicator = FastNetNeuronCommunicator(mock_platform, "COM3", mock_communicator_config)

        # Case 1: Successful Intentional Hold (> 2.5s)
        communicator._process_wp('P')

        self.assertEqual(mock_platform.soft_power_held_time, 1000.0)
        mock_platform.machine.events.post.assert_called_with('fast_soft_power_switch_active')

        # Advance our mock clock forward by 3 seconds (> 2.5s threshold)
        mock_platform.machine.clock.get_time.return_value = 1003.0

        # Simulate a watchdog response after button release (WD:P)
        communicator._process_wd('P')

        # Verify that the hold state was reset and the shutdown command was issued
        self.assertIsNone(mock_platform.soft_power_held_time)
        mock_platform.machine.events.post.assert_any_call('fast_soft_power_switch_inactive')
        mock_platform.report_soft_power_down_request.assert_called_once()

        # Case 2: Aborted/Short Accidental Press (< 2.5s)
        mock_platform.report_soft_power_down_request.reset_mock()
        mock_platform.soft_power_held_time = None
        mock_platform.machine.clock.get_time.return_value = 2000.0

        communicator._process_wp('P')
        self.assertEqual(mock_platform.soft_power_held_time, 2000.0)

        # Only hold 0.5 seconds (< 2.5s threshold)
        mock_platform.machine.clock.get_time.return_value = 2000.5

        communicator._process_wd('P')

        # Verify that state was cleared but the shutdown request was SAFELY blocked
        self.assertIsNone(mock_platform.soft_power_held_time)
        mock_platform.report_soft_power_down_request.assert_not_called()

    def test_communicator_stopping_sends_serial_power_down_command(self):
        """Verify that stopping the communicator formats and sends the final serial delay command."""
        mock_platform = MagicMock()
        mock_platform.machine = MagicMock()

        # Simulate an approved active shutdown state
        mock_platform.machine.soft_power_down_active = True

        # Configure the exact platform values from your fast.py updates
        mock_platform.soft_power_down_final_delay_ms = 4000  # 4000ms converts to FA0 in hex

        mock_communicator_config = {'debug': False, 'io_loop': {}, 'console_log': 'none', 'file_log': 'none'}
        communicator = FastNetNeuronCommunicator(mock_platform, "COM3", mock_communicator_config)

        # Safely patch the slotted class method to track outbound transmissions
        with patch.object(FastNetNeuronCommunicator, 'send_and_forget') as mock_send:
            # Trigger the teardown routine
            communicator.stopping()

            # Assertions
            mock_send.assert_any_call('WD:1')
            mock_send.assert_any_call('WP:FA0')
