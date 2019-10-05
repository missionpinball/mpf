from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase
import mpf.platforms.pololu_maestro


class TestPololuMaestro(MpfTestCase):

    def get_config_file(self):
        return 'pololu_maestro.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/pololu_maestro/'

    def get_platform(self):
        return False

    def setUp(self):
        self.serial = MagicMock()
        mpf.platforms.pololu_maestro.serial = MagicMock()
        mpf.platforms.pololu_maestro.serial.Serial.return_value = self.serial
        super().setUp()

    def _build_message(self, command, number, value, controller=12):
        lsb = value & 0x7f  # 7 bits for least significant byte
        msb = (value >> 7) & 0x7f  # shift 7 and take next 7 bits for msb
        # Send Pololu intro, device number, command, channel, and target
        # lsb/msb
        return bytes([0xaa, controller, command, number, lsb, msb])

    def test_servo_go_to_position(self):
        # go to position 1.0 (on of the ends)
        self.machine.servos["servo1"].go_to_position(1.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(0x04, 1, 9000))
        # go to position 0.0 (other end)
        self.machine.servos["servo1"].go_to_position(0.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(0x04, 1, 3000))

        self.serial.reset_mock()
        # go to position 1.0 (on of the ends)
        self.machine.servos["servo2"].go_to_position(1.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(0x04, 2, 7800))
        # go to position 0.0 (other end)
        self.machine.servos["servo2"].go_to_position(0.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(0x04, 2, 4200))
        # go to position 0.0 (middle)
        self.machine.servos["servo2"].go_to_position(0.5)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(0x04, 2, 6000))

    def test_daisy_chaining(self):
        # go to position 1.0 (on of the ends)
        self.machine.servos["servo1_controller_13"].go_to_position(1.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(0x04, 1, 9000, controller=13))

    def test_servo_set_speed(self):
        # test setting speed in config
        self.assertEqual(0.5, self.machine.servos["servo1"].speed_limit)
        # test standard value
        self.assertEqual(-1.0, self.machine.servos["servo2"].speed_limit)

        self.machine.servos["servo1"].set_speed_limit(-1.0)
        self.serial.write.assert_called_with(self._build_message(0x07, 1, 0))
        self.machine.servos["servo1"].set_speed_limit(0.0)
        self.serial.write.assert_called_with(self._build_message(0x07, 1, 1))
        self.machine.servos["servo1"].set_speed_limit(0.5)
        self.serial.write.assert_called_with(self._build_message(0x07, 1, 18))
        self.machine.servos["servo1"].set_speed_limit(1.0)

    def test_servo_set_acceleration(self):
        # test setting acceleration in config
        self.assertEqual(0.5, self.machine.servos["servo1"].acceleration_limit)
        # test standard value
        self.assertEqual(-1.0, self.machine.servos["servo2"].acceleration_limit)

        self.machine.servos["servo1"].set_speed_limit(-1.0)
        self.serial.write.assert_called_with(self._build_message(0x07, 1, 0))
        self.machine.servos["servo1"].set_speed_limit(0.0)
        self.serial.write.assert_called_with(self._build_message(0x07, 1, 1))
        self.machine.servos["servo1"].set_acceleration_limit(0.5)
        self.serial.write.assert_called_with(self._build_message(0x09, 1, 180))
        self.machine.servos["servo1"].set_acceleration_limit(1.0)
        self.serial.write.assert_called_with(self._build_message(0x09, 1, 255))
