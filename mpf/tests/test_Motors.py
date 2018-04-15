from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestMotors(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/motor/'

    def testMotorizedDropTargetBank(self):
        motor = self.machine.motors["motorized_drop_target_bank"]
        coil = self.machine.digital_outputs["c_motor_run"]
        coil.enable = MagicMock()
        coil.disable = MagicMock()

        # reset should move it down
        motor.reset()
        self.advance_time_and_run()
        coil.enable.assert_called_with()
        coil.enable = MagicMock()
        assert not coil.disable.called

        # it goes up. nothing should happen
        self.hit_switch_and_run("s_position_up", 1)
        assert not coil.enable.called
        assert not coil.disable.called

        # it leaves up position
        self.release_switch_and_run("s_position_up", 1)
        assert not coil.enable.called
        assert not coil.disable.called

        self.advance_time_and_run(5)
        # it goes down. motor should stop
        self.hit_switch_and_run("s_position_down", 1)
        assert not coil.enable.called
        coil.disable.assert_called_with()
        coil.disable = MagicMock()

        # should not start motor
        self.post_event("go_down2")
        self.advance_time_and_run()
        assert not coil.enable.called
        coil.disable.assert_called_with()
        coil.disable = MagicMock()

        # go up
        self.post_event("go_up")
        self.advance_time_and_run()
        coil.enable.assert_called_with()
        coil.enable = MagicMock()
        assert not coil.disable.called

        # it leaves down position
        self.release_switch_and_run("s_position_down", 0)
        assert not coil.enable.called
        assert not coil.disable.called

        self.advance_time_and_run(5)
        # it goes up. motor should stop
        self.hit_switch_and_run("s_position_up", 1)
        assert not coil.enable.called
        coil.disable.assert_called_with()
        coil.disable = MagicMock()

    def testMotorToyWithTwoEndSwitches(self):
        slimer = self.machine.motors["ghostbusters_slimer"]
        motor_left = self.machine.digital_outputs["c_slimer_motor_forward"].hw_driver
        motor_right = self.machine.digital_outputs["c_slimer_motor_backward"].hw_driver

        self.assertEqual(1.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)

        self.hit_switch_and_run("s_slimer_home", 1)
        self.assertEqual(0.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)

        slimer.go_to_position("away")
        self.advance_time_and_run()
        self.assertEqual(0.0, motor_left.current_brightness)
        self.assertEqual(1.0, motor_right.current_brightness)
        self.release_switch_and_run("s_slimer_home", 1)
        self.hit_switch_and_run("s_slimer_away", 1)

        self.assertEqual(0.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)

        slimer.go_to_position("away")
        self.assertEqual(0.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)

        slimer.go_to_position("home")
        self.assertEqual(1.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)

        self.hit_switch_and_run("s_slimer_home", 1)
        self.assertEqual(0.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)
