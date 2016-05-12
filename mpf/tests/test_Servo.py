from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestServo(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/servo/'

    def test_servo_go_to_position(self):
        # full range servo
        self.machine.default_platform.servo_go_to_position = MagicMock()
        # go to position 1.0 (on of the ends)
        self.machine.servos.test_servo.go_to_position(1.0)
        # assert that platform got called
        self.machine.default_platform.servo_go_to_position.assert_called_with(2, 1.0)
        # go to position 0.0 (other end)
        self.machine.servos.test_servo.go_to_position(0.0)
        # assert that platform got called
        self.machine.default_platform.servo_go_to_position.assert_called_with(2, 0.0)

        # limited range servo (like most ones)
        self.machine.default_platform.servo_go_to_position = MagicMock()
        # go to position 1.0 (on of the ends)
        self.machine.servos.limited_servo.go_to_position(1.0)
        # assert that platform got called
        self.machine.default_platform.servo_go_to_position.assert_called_with(1, 0.8)
        # go to position 0.0 (other end)
        self.machine.servos.limited_servo.go_to_position(0.0)
        # assert that platform got called
        self.machine.default_platform.servo_go_to_position.assert_called_with(1, 0.2)
        # go to position 0.0 (middle)
        self.machine.servos.limited_servo.go_to_position(0.5)
        # assert that platform got called
        self.machine.default_platform.servo_go_to_position.assert_called_with(1, 0.5)

    def test_events(self):
        self.machine.default_platform.servo_go_to_position = MagicMock()

        # post reset event
        self.post_event("test_reset")
        # should go to reset position
        self.machine.default_platform.servo_go_to_position.assert_called_with(2, 0.5)

        # post another defined event
        self.post_event("test_00")
        self.machine.default_platform.servo_go_to_position.assert_called_with(2, 0.0)

        # post another defined event
        self.post_event("test_01")
        self.machine.default_platform.servo_go_to_position.assert_called_with(2, 0.1)

        # post another defined event
        self.post_event("test_10")
        self.machine.default_platform.servo_go_to_position.assert_called_with(2, 1.0)
