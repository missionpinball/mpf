from unittest.mock import MagicMock,Mock
from mpf.tests.MpfTestCase import MpfTestCase
import mpf.platforms.trinamics_steprocker

class TestTrinamicsStepRocker(MpfTestCase):

    def get_config_file(self):
        return 'trinamics_steprocker.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/trinamics_steprocker/'

    def get_platform(self):
        return False

    def test_rotary(self):
        return
        stepper = self.machine.steppers["velocityStepper"]

        # spin clockwise, 45 degrees per second
        stepper.move_vel_mode( 45 )
        self.assertEqual( 45, stepper._cachedVelocity )

        # stop
        stepper.stop()
        self.assertEqual( 0, stepper._cachedVelocity )

        # spin counter clockwise
        stepper.move_vel_mode( -60 )
        self.assertEqual( -60, stepper._cachedVelocity )

        # stop
        stepper.stop()
        self.assertEqual( 0, stepper._cachedVelocity )

        # try to go too fast
        with self.assertRaises(ValueError):
            stepper.move_vel_mode( stepper.config['velocity_limit'] + 0.01 )

        # try a home / should be rejected
        with self.assertRaises(RuntimeError):
            stepper.home()

        # try a position move / should be rejected
        with self.assertRaises(RuntimeError):
            stepper._move_to_absolute_position(42)

        # try a relative move / should be rejected
        with self.assertRaises(RuntimeError):
            stepper.move_rel_pos( 42 )

    def test_AbsPositionTest(self):
        stepper = self.machine.steppers["positionStepper"]

        # check home/reset
        self.assertEqual(0.0, stepper._current_position)

        # min/max in test file is 0,1 scaling setup for 1.0 = 1 revolution
        stepper._move_to_absolute_position(0.5)
        self.machine.clock.loop.run_until_complete(self.machine.events.wait_for_event('stepper_positionStepper_ready'))
        self.assertEqual(0.5, stepper._current_position)

        # Go to max
        stepper._move_to_absolute_position(1.0)
        self.machine.clock.loop.run_until_complete(self.machine.events.wait_for_event('stepper_positionStepper_ready'))
        self.assertEqual(1.0, stepper._current_position)

        # Go to min
        stepper._move_to_absolute_position(0.0)
        self.machine.clock.loop.run_until_complete(self.machine.events.wait_for_event('stepper_positionStepper_ready'))
        self.assertEqual(0.0, stepper._current_position)

    def setUp(self):
        #self.MockTMCLLib = MagicMock(spec=mpf.platforms.trinamics_steprocker.TMCLDevice)
        self.MockTMCLLib = MagicMock()
        self.MockTMCLLib.rfs.return_value = int(0)
        self.MockTMCLLib.gap.side_effect = self.mock_gap
        self.MockTMCLLib.mvp.side_effect = self.mock_mvp
        self._trinam_pos = 0
        mpf.platforms.trinamics_steprocker.TMCLDevice = MagicMock()
        mpf.platforms.trinamics_steprocker.TMCLDevice.return_value = self.MockTMCLLib
        super().setUp()

    # Mock functionality needed
    def mock_mvp(self, motor_number, cmdtype, value):
        self._trinam_pos = value

    def mock_gap(self, mn, param):
        global _trinam_pos
        if param == 1:
            return self._trinam_pos
        elif param == 8:
            return 1

