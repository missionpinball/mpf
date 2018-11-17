from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestStepper(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/stepper/'

    def test_linearstepper(self):
        # full range servo
        stepper = self.machine.steppers.linearAxis_stepper
        # verify - now at zero both in stepper and in HW
        self.assertEqual(0.0, stepper._current_position)

        # go to min
        commandPos = stepper.config['pos_min']
        stepper._move_to_absolute_position(commandPos)
        self.machine.clock.loop.run_until_complete(
            self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready"))
        self.assertAlmostEqual(commandPos, stepper._current_position, 0)

        # go to max
        commandPos = stepper.config['pos_max']
        stepper._move_to_absolute_position(commandPos)
        self.machine.clock.loop.run_until_complete(
            self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready"))
        self.assertAlmostEqual(commandPos, stepper._current_position, 0)

        # try out of bounds
        with self.assertRaises(ValueError):
            commandPos = stepper.config['pos_min'] - 0.01
            stepper._move_to_absolute_position(commandPos)

        with self.assertRaises(ValueError):
            commandPos = stepper.config['pos_max'] + 0.01
            stepper._move_to_absolute_position(commandPos)

        # relative +/-
        stepper._move_to_absolute_position(0)
        self.machine.clock.loop.run_until_complete(
            self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready"))
        self.assertEqual(0, stepper._current_position)

        # try relative out of bounds
        # at zero, a relative move of min or max limit is equiv to absolute
        stepper._move_to_absolute_position(0)
        self.assertEqual(0, stepper._current_position)

    def test_rotary(self):
        return
        stepper = self.machine.steppers.rotaryMotor_stepper

        # spin clockwise
        stepper.move_vel_mode( 1000 )
        self.assertEqual( 1000, stepper._cachedVelocity )

        # stop
        stepper.move_vel_mode( 0 )
        self.assertEqual( 0, stepper._cachedVelocity )

        # spin counter clockwise
        stepper.move_vel_mode( -1000 )
        self.assertEqual( -1000, stepper._cachedVelocity )

        # stop
        stepper.move_vel_mode( 0 )
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

    def test_stepper_events(self):
        stepper = self.machine.steppers.linearAxis_stepper

        # post reset event
        event_future = self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready")
        self.post_event("test_reset")
        self.machine.clock.loop.run_until_complete(event_future)
        # should go to reset position
        self.assertEqual(0.0, stepper._current_position)

        # post another defined event
        event_future = self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready")
        self.post_event("test_00")
        self.machine.clock.loop.run_until_complete(event_future)
        self.assertEqual(-5.0, stepper._current_position, 0)

        # post another defined event
        event_future = self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready")
        self.post_event("test_01")
        self.machine.clock.loop.run_until_complete(event_future)
        self.assertEqual(999.0, stepper._current_position, 0)

        # post another defined event
        event_future = self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready")
        self.post_event("test_10")
        self.machine.clock.loop.run_until_complete(event_future)
        self.assertEqual(500.0, stepper._current_position, 0)

    def test_ball_search(self):
        stepper = self.machine.steppers.linearAxis_stepper

        self.machine.playfields.playfield.config['enable_ball_search'] = True
        self.machine.playfields.playfield.balls += 1

        event_future = self.machine.events.wait_for_event("stepper_linearAxis_stepper_ready")
        self.post_event("test_10")
        self.machine.clock.loop.run_until_complete(event_future)
        self.assertEqual(500, stepper._current_position)

        # wait until ball search started
        event_future = self.machine.events.wait_for_event("ball_search_started")
        self.machine.clock.loop.run_until_complete(event_future)

        # it will first go to ball search max
        self.advance_time_and_run(.5)
        self.assertEqual(0, stepper._current_position)

        self.advance_time_and_run(5)
        # and then to min
        self.assertEqual(1, stepper._current_position)

        # wait until ball search failed
        event_future = self.machine.events.wait_for_event("ball_search_failed")
        self.machine.clock.loop.run_until_complete(event_future)

        # stepper should restore to previous location
        self.advance_time_and_run(.5)
        self.assertEqual(500, stepper._current_position)
