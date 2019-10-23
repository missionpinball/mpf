from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase


class TestServo(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/servo/'

    def test_servo_go_to_position(self):
        # full range servo
        servo = self.machine.servos["test_servo"]
        # go to position 1.0 (on of the ends)
        servo.go_to_position(1.0)
        # assert that platform got called
        self.assertEqual(1.0, servo.hw_servo.current_position)
        # go to position 0.0 (other end)
        servo.go_to_position(0.0)
        # assert that platform got called
        self.assertEqual(0.0, servo.hw_servo.current_position)

        # limited range servo (like most ones)
        servo = self.machine.servos["limited_servo"]
        # go to position 1.0 (on of the ends)
        servo.go_to_position(1.0)
        # assert that platform got called
        self.assertEqual(0.8, servo.hw_servo.current_position)
        # go to position 0.0 (other end)
        servo.go_to_position(0.0)
        # assert that platform got called
        self.assertEqual(0.2, servo.hw_servo.current_position)
        # go to position 0.0 (middle)
        servo.go_to_position(0.5)
        # assert that platform got called
        self.assertEqual(0.5, servo.hw_servo.current_position)

    def test_events(self):
        servo = self.machine.servos["test_servo"]

        # post reset event
        self.post_event("test_reset")
        # should go to reset position
        self.assertEqual(0.5, servo.hw_servo.current_position)

        # post another defined event
        self.post_event("test_00")
        self.assertEqual(0.0, servo.hw_servo.current_position)

        # post another defined event
        self.post_event("test_01")
        self.assertEqual(0.1, servo.hw_servo.current_position)

        # post another defined event
        self.post_event("test_10")
        self.assertEqual(1.0, servo.hw_servo.current_position)
