import os
import subprocess
import warnings

from unittest.mock import patch, MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestSoftPowerDown(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/soft_power_down/'

    def setUp(self):
        super().setUp()
        self.machine.soft_power_down_active = False

        # Suppress dangling process warnings from our mock shell commands
        warnings.simplefilter("ignore", ResourceWarning)

        self.mock_event('machine_will_shutdown')
        self.mock_event('machine_abort_shutdown')

    def test_shutdown_request_denied_by_handler(self):
        """Verify that if a registered game handler returns False, the soft shutdown aborts."""
        def veto_handler(**kwargs):
            return False

        self.machine.events.add_handler('machine_request_shutdown', veto_handler)

        self.machine.events.post('request_soft_shutdown', reason='Testing')
        self.advance_time_and_run(1.0)  # Advance far enough to process async handlers

        self.assertFalse(self.machine.soft_power_down_active)
        self.assertFalse(self.machine.stop_future.done())

        self.assertEventCalled('machine_abort_shutdown')

    @patch('subprocess.Popen')
    def test_shutdown_request_approved_and_executes_cmd(self, mock_popen):
        """Verify that an approved shutdown posts events and fires the shell command."""
        cmd = 'echo shutting down'
        self.machine.config['machine']['soft_shutdown_exit_command'] = cmd

        self.machine.soft_power_down_active = False

        self.machine.events.post('request_soft_shutdown')
        self.advance_time_and_run(1.0)  # Advance far enough to flush the async future queue

        self.assertTrue(self.machine.soft_power_down_active)
        self.assertTrue(self.machine.stop_future.done())

        self.assertEventCalled('machine_will_shutdown')

        with patch.object(self.machine.clock.loop, 'close'):
            self.machine._do_stop()

        mock_popen.assert_called_once_with(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        self.machine._do_stop = MagicMock()
