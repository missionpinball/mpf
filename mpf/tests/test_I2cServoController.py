from mpf.tests.MpfTestCase import MpfTestCase


class TestI2cServoController(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/i2c_servo_controller/'

    def get_platform(self):
        return False

    def test_servo_move(self):
        self.assertEqual(0x40, self.machine.servos["servo1"].hw_servo.i2c_device.number)
        self.assertEqual(3, self.machine.servos["servo1"].hw_servo.number)
        self.assertEqual("bus1-64", self.machine.servos["servo2"].hw_servo.i2c_device.number)
        self.assertEqual(7, self.machine.servos["servo2"].hw_servo.number)
        self.assertEqual(0x40, self.machine.servos["servo3"].hw_servo.i2c_device.number)
        self.assertEqual(4, self.machine.servos["servo3"].hw_servo.number)
        self.assertEqual(self.machine.servos["servo1"].hw_servo.i2c_device,
                         self.machine.servos["servo3"].hw_servo.i2c_device)#

        # move servo1
        self.assertEqual(119, self.machine.servos["servo1"].hw_servo.i2c_device.data[0x08 + 3 * 4])
        self.assertEqual(1, self.machine.servos["servo1"].hw_servo.i2c_device.data[0x09 + 3 * 4])
        self.machine.servos["servo1"].go_to_position(1.0)
        self.assertEqual(88, self.machine.servos["servo1"].hw_servo.i2c_device.data[0x08 + 3 * 4])
        self.assertEqual(2, self.machine.servos["servo1"].hw_servo.i2c_device.data[0x09 + 3 * 4])

        # move servo2
        self.assertEqual(119, self.machine.servos["servo2"].hw_servo.i2c_device.data[0x08 + 7 * 4])
        self.assertEqual(1, self.machine.servos["servo2"].hw_servo.i2c_device.data[0x09 + 7 * 4])
        self.machine.servos["servo2"].go_to_position(1.0)
        self.assertEqual(88, self.machine.servos["servo2"].hw_servo.i2c_device.data[0x08 + 7 * 4])
        self.assertEqual(2, self.machine.servos["servo2"].hw_servo.i2c_device.data[0x09 + 7 * 4])
