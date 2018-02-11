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
        # home
        stepper.home()
        # verify - now at zero both in stepper and in HW
        self.assertEqual(0.0, stepper.current_position())

        # go to min
        commandPos = stepper.config['pos_min']
        stepper.move_abs_pos( commandPos )
        self.assertAlmostEqual(commandPos, stepper.current_position(), 0)

        # go to max
        commandPos = stepper.config['pos_max']
        stepper.move_abs_pos( commandPos )
        self.assertAlmostEqual(commandPos, stepper.current_position(), 0)

        # try out of bounds
        with self.assertRaises(ValueError):
            commandPos = stepper.config['pos_min'] - 0.01
            stepper.move_abs_pos( commandPos )
        
        with self.assertRaises(ValueError):
            commandPos = stepper.config['pos_max'] + 0.01
            stepper.move_abs_pos( commandPos )

        # try a velocity mode command / should be rejected
        with self.assertRaises(RuntimeError):
            stepper.move_vel_mode( 0 )

        # relative +/-
        stepper.move_abs_pos( 0 )
        self.assertEqual(0, stepper.current_position())
        stepper.move_rel_pos( 10 )
        stepper.move_rel_pos( -10 )
        self.assertEqual(0, stepper.current_position())

        # try relative out of bounds
        # at zero, a relative move of min or max limit is equiv to absolute
        stepper.move_abs_pos( 0 )
        self.assertEqual(0, stepper.current_position())

        with self.assertRaises(ValueError):
            commandPos = stepper.config['pos_max'] + 0.01
            stepper.move_rel_pos( commandPos )

        with self.assertRaises(ValueError):
            commandPos = stepper.config['pos_max'] + 0.01
            stepper.move_rel_pos( commandPos )

    def test_rotary(self):
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
            stepper.move_abs_pos( 42 )          
        
        # try a relative move / should be rejected
        with self.assertRaises(RuntimeError):
            stepper.move_rel_pos( 42 )          

    def test_stepper_events(self):
        stepper = self.machine.steppers.linearAxis_stepper

        # post reset event
        self.post_event("test_reset")
        # should go to reset position
        self.assertEqual(0.0, stepper.current_position())

        # post another defined event
        self.post_event("test_00")
        self.assertEqual(-5.0, stepper.current_position(), 0)

        # post another defined event
        self.post_event("test_01")
        self.assertEqual(999.0, stepper.current_position(), 0)

        # post another defined event
        self.post_event("test_10")
        self.assertEqual(500.0, stepper.current_position(), 0)
