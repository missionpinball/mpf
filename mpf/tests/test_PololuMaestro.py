from unittest.mock import MagicMock
from mpf.tests.MpfTestCase import MpfTestCase
import mpf.platforms.pololu_maestro


class TestPololuMaestro(MpfTestCase):

    def getConfigFile(self):
        return 'pololu_maestro.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/pololu_maestro/'

    def getOptions(self):
        options = super().getOptions()
        options['force_platform'] = False
        return options

    def setUp(self):
        self.serial = MagicMock()
        mpf.platforms.pololu_maestro.serial = MagicMock()
        mpf.platforms.pololu_maestro.serial.Serial.return_value = self.serial
        super().setUp()

    def _build_message(self, number, value):
        lsb = value & 0x7f  # 7 bits for least significant byte
        msb = (value >> 7) & 0x7f  # shift 7 and take next 7 bits for msb
        # Send Pololu intro, device number, command, channel, and target
        # lsb/msb
        return bytes([0xaa, 0xc, 0x04, number, lsb, msb])

    def test_servo_go_to_position(self):
        # go to position 1.0 (on of the ends)
        self.machine.servos.servo1.go_to_position(1.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(1, 9000))
        # go to position 0.0 (other end)
        self.machine.servos.servo1.go_to_position(0.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(1, 3000))

        self.serial.reset_mock()
        # go to position 1.0 (on of the ends)
        self.machine.servos.servo2.go_to_position(1.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(2, 7800))
        # go to position 0.0 (other end)
        self.machine.servos.servo2.go_to_position(0.0)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(2, 4200))
        # go to position 0.0 (middle)
        self.machine.servos.servo2.go_to_position(0.5)
        # assert that platform got called
        self.serial.write.assert_called_with(self._build_message(2, 6000))
