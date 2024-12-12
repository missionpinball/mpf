from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase, test_config


class TestMotors(MpfTestCase):

    def get_machine_path(self):
        return 'tests/machine_files/motor/'

    @test_config("drop_target.yaml")
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

    @test_config("ghostbusters.yaml")
    def testMotorToyWithTwoEndSwitches(self):
        slimer = self.machine.motors["ghostbusters_slimer"]
        motor_left = self.machine.digital_outputs["c_slimer_motor_forward"].hw_driver
        motor_right = self.machine.digital_outputs["c_slimer_motor_backward"].hw_driver
        self.assertPlaceholderEvaluates("left", "device.motors.ghostbusters_slimer.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.ghostbusters_slimer.last_position")
        self.assertPlaceholderEvaluates("home", "device.motors.ghostbusters_slimer.target_position")

        self.assertEqual(1.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)

        self.hit_switch_and_run("s_slimer_home", 1)
        self.assertEqual(0.0, motor_left.current_brightness)
        self.assertEqual(0.0, motor_right.current_brightness)
        self.assertPlaceholderEvaluates("stopped", "device.motors.ghostbusters_slimer.move_direction")
        self.assertPlaceholderEvaluates("home", "device.motors.ghostbusters_slimer.last_position")
        self.assertPlaceholderEvaluates("home", "device.motors.ghostbusters_slimer.target_position")

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

    @test_config("multiposition_motor.yaml")
    def testMotorWithMultipleSwitches(self):
        """Test motor with home switch on the right."""
        self.assertPlaceholderEvaluates("right", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.multiposition_motor.last_position")

        self.hit_switch_and_run("s_multiposition_motor_3", 1)
        self.assertPlaceholderEvaluates("right", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates("position3", "device.motors.multiposition_motor.last_position")

        self.release_switch_and_run("s_multiposition_motor_3", 1)
        self.hit_switch_and_run("s_multiposition_motor_4", 1)
        self.assertPlaceholderEvaluates("stopped", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates("position4", "device.motors.multiposition_motor.last_position")

    @test_config("multiposition_motor.yaml")
    def testMotorHitsUnexpectedEndSwitch(self):
        """Test if motor stops when it reached an unexpected end switch."""
        self.assertPlaceholderEvaluates("right", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.multiposition_motor.last_position")

        # for some reason the motor reached the left end (while moving right)
        self.hit_switch_and_run("s_multiposition_motor_1", 1)
        self.assertPlaceholderEvaluates("stopped", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates("position1", "device.motors.multiposition_motor.last_position")

        # move motor again
        self.machine.motors["multiposition_motor"].go_to_position("position3")
        self.advance_time_and_run(1)
        # it should move right as it is on the left stop
        self.assertPlaceholderEvaluates("right", "device.motors.multiposition_motor.move_direction")

        self.release_switch_and_run("s_multiposition_motor_1", 1)

        # for some reason it misses position3 and bumps in to the end stop at the right
        self.hit_switch_and_run("s_multiposition_motor_4", 1)
        self.assertPlaceholderEvaluates("stopped", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates("position4", "device.motors.multiposition_motor.last_position")

    @test_config("multiposition_motor_start_on_end_switch.yaml")
    def testMotorOnEndSwitchAtStart(self):
        """Motor is at the right end switch but that is not home."""
        # motor should move left right away
        self.assertPlaceholderEvaluates("left", "device.motors.multiposition_motor.move_direction")

    @test_config("multiposition_motor.yaml")
    def testStuckSwitches(self):
        """Motor should stop when multiple position switches are active."""
        self.assertPlaceholderEvaluates("right", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.multiposition_motor.last_position")

        # two switches are stuck - motor should stop
        self.hit_switch_and_run("s_multiposition_motor_2", 1)
        self.hit_switch_and_run("s_multiposition_motor_3", 1)
        self.assertPlaceholderEvaluates("stopped", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.multiposition_motor.last_position")

        # motor should not move
        self.machine.motors["multiposition_motor"].go_to_position("position1")
        self.advance_time_and_run(1)
        self.assertPlaceholderEvaluates("stopped", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.multiposition_motor.last_position")

        # switch 2 becomes unstuck
        self.release_switch_and_run("s_multiposition_motor_2", 1)

        # motor should move again
        self.machine.motors["multiposition_motor"].go_to_position("position2")
        self.advance_time_and_run(1)
        self.assertPlaceholderEvaluates("left", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.multiposition_motor.last_position")

        self.release_switch_and_run("s_multiposition_motor_3", 1)
        self.hit_switch_and_run("s_multiposition_motor_2", 1)
        self.assertPlaceholderEvaluates("stopped", "device.motors.multiposition_motor.move_direction")
        self.assertPlaceholderEvaluates("position2", "device.motors.multiposition_motor.last_position")

    @test_config("multiposition_motor_home_in_the_middle.yaml")
    def testMotorWithMultipleSwitchesAndHomeInTheMiddle(self):
        """Motor starts moving to the right but should reverse when it knows its position."""
        self.assertPlaceholderEvaluates("right", "device.motors.multiposition_motor2.move_direction")
        self.assertPlaceholderEvaluates(None, "device.motors.multiposition_motor2.last_position")

        # first known position - motor reverses
        self.hit_switch_and_run("s_multiposition_motor_3", 1)
        self.assertPlaceholderEvaluates("left", "device.motors.multiposition_motor2.move_direction")
        self.assertPlaceholderEvaluates("position3", "device.motors.multiposition_motor2.last_position")

        # motor reaches home
        self.release_switch_and_run("s_multiposition_motor_3", 1)
        self.hit_switch_and_run("s_multiposition_motor_2", 1)
        self.assertPlaceholderEvaluates("stopped", "device.motors.multiposition_motor2.move_direction")
        self.assertPlaceholderEvaluates("position2", "device.motors.multiposition_motor2.last_position")
