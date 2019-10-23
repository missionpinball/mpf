import asyncio

from mpf.platforms.pololu import pololu_tic
from mpf.tests.MpfTestCase import MpfTestCase
import ruamel.yaml


class TestPololuTic(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/pololu_tic/'

    def get_platform(self):
        return False

    def _ticcmd_async(self, *args):
        if args == ("-s", "--full"):
            return ruamel.yaml.dump({
                'Errors currently stopping the motor': [],
                'Current position': self._position
            })
        elif args == ('--reset-command-timeout',):
            return ""

        if args not in self.expected_commands:
            raise AssertionError("Unexpected command {}. Expected: {}".format(args, self.expected_commands))

        return_value = self.expected_commands[args]
        del self.expected_commands[args]
        return return_value

    def setUp(self):
        self._position = 0
        self.expected_commands = {
            ('--energize',): "",
            ('--exit-safe-start',): "",
            ('--current', '192'): "",
            ('--max-decel', '40000'): "",
            ('--max-accel', '40000'): "",
            ('--starting-speed', '0'): "",
            ('--max-speed', '2000000'): "",
            ('--step-mode', '1'): "",
            ('--velocity', '2000000'): ""
        }
        def _create_fake_thread(self_inner):
            self_inner.stop_future = asyncio.Future(loop=self.loop)
            self_inner.loop = self.loop

        def _stop_thread(self_inner):
            pass

        pololu_tic.PololuTiccmdWrapper._start_thread = _create_fake_thread
        pololu_tic.PololuTiccmdWrapper._stop_thread = _stop_thread
        pololu_tic.PololuTiccmdWrapper._run_subprocess_ticcmd = self._ticcmd_async

        super().setUp()
        self.assertFalse(self.expected_commands)

    def test_tic(self):
        """Test Tic stepper."""
        stepper = self.machine.steppers["stepper1"]

        # stepper arrives at home
        self.expected_commands = {
            ('--halt-and-hold',): "",
            ('--halt-and-set-position', '0'): ""
        }
        self.hit_switch_and_run("s_home", 1)
        self.assertFalse(self.expected_commands)

        # move stepper
        self.expected_commands = {
            ('--position', '20'): ""
        }
        self.post_event("test_01")
        self.advance_time_and_run(.1)
        self.assertFalse(self.expected_commands)
        self.assertEqual(20, stepper._target_position)
        self.assertEqual(0, stepper._current_position)

        # stepper arrives at position
        self._position = 20
        self.advance_time_and_run(.1)
        self.assertEqual(20, stepper._target_position)
        self.assertEqual(20, stepper._current_position)

        # move stepper
        self.expected_commands = {
            ('--position', '50'): ""
        }
        self.post_event("test_10")
        self.advance_time_and_run(.1)
        self.assertFalse(self.expected_commands)
        self.assertEqual(50, stepper._target_position)
        self.assertEqual(20, stepper._current_position)

        # stepper arrives at position
        self._position = 50
        self.advance_time_and_run(.1)
        self.assertEqual(50, stepper._target_position)
        self.assertEqual(50, stepper._current_position)

        # prevent crash during shutdown
        self.expected_commands = {
            ('--halt-and-hold',): ""
        }
