from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.events import event_handler

class TestTrinamicsStepRocker(MpfTestCase):

    def getConfigFile(self):
        return 'trinamics_steprocker.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/trinamics_steprocker/'

    def getOptions(self):
        options = super().getOptions()
        options['force_platform'] = False
        return options

    def test_rotary(self):
        stepper = self.machine.steppers.velocityStepper

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
            stepper.move_abs_pos( 42 )
        
        # try a relative move / should be rejected
        with self.assertRaises(RuntimeError):
            stepper.move_rel_pos( 42 )

    def test_homing(self):
        move_complete = self.machine.events.wait_for_event('stepper_positionStepper_ready')
        stepper = self.machine.steppers.positionStepper

        stepper.home()
        self.machine.clock.loop.run_until_complete(move_complete)
        self.assertEqual( 0, stepper.currentPosition())

    def test_AbsPositionTest(self):
        stepper = self.machine.steppers.positionStepper

        #home
        stepper.home()
        self.machine.clock.loop.run_until_complete(self.machine.events.wait_for_event('stepper_positionStepper_ready'))
        self.assertEqual( 0.0, stepper.currentPosition())

        # min/max in test file is 0,1 scaling setup for 1.0 = 1 revolution
        stepper.move_abs_pos(0.5)
        self.machine.clock.loop.run_until_complete(self.machine.events.wait_for_event('stepper_positionStepper_ready'))
        self.assertEqual( 0.5, stepper.currentPosition())

        # Go to max
        stepper.move_abs_pos(1.0)
        self.machine.clock.loop.run_until_complete(self.machine.events.wait_for_event('stepper_positionStepper_ready'))
        self.assertEqual( 1.0, stepper.currentPosition())

        # Go to min
        stepper.move_abs_pos(0.0)
        self.machine.clock.loop.run_until_complete(self.machine.events.wait_for_event('stepper_positionStepper_ready'))
        self.assertEqual( 0.0, stepper.currentPosition())

    def setUp(self):
        #self._moveComplete = False
        super().setUp()
    
    @event_handler(1)
    def moveComplete(self,**kwargs):
        del kwargs
        self._moveComplete = True

    #def setUp(self):
    #     self.serial = MagicMock()
    #     mpf.platforms.trinamics_steprocker.serial = MagicMock()
    #     mpf.platforms.trinamics_steprocker.serial.Serial.return_value = self.serial
    #     super().setUp()

    # def _build_message(self, number, value):
    #     lsb = value & 0x7f  # 7 bits for least significant byte
    #     msb = (value >> 7) & 0x7f  # shift 7 and take next 7 bits for msb
    #     # Send Pololu intro, device number, command, channel, and target
    #     # lsb/msb
    #     return chr(0xaa) + chr(0xc) + chr(0x04) + chr(number) + chr(lsb) + chr(msb)

    # def test_servo_go_to_position(self):
    #     # go to position 1.0 (on of the ends)
    #     self.machine.servos.servo1.go_to_position(1.0)
    #     # assert that platform got called
    #     self.serial.write.assert_called_with(self._build_message(1, 9000))
    #     # go to position 0.0 (other end)
    #     self.machine.servos.servo1.go_to_position(0.0)
    #     # assert that platform got called
    #     self.serial.write.assert_called_with(self._build_message(1, 3000))

    #     self.serial.reset_mock()
    #     # go to position 1.0 (on of the ends)
    #     self.machine.servos.servo2.go_to_position(1.0)
    #     # assert that platform got called
    #     self.serial.write.assert_called_with(self._build_message(2, 7800))
    #     # go to position 0.0 (other end)
    #     self.machine.servos.servo2.go_to_position(0.0)
    #     # assert that platform got called
    #     self.serial.write.assert_called_with(self._build_message(2, 4200))
    #     # go to position 0.0 (middle)
    #     self.machine.servos.servo2.go_to_position(0.5)
    #     # assert that platform got called
    #     self.serial.write.assert_called_with(self._build_message(2, 6000))
