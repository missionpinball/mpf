from unittest.mock import MagicMock, call

from mpf.tests.MpfTestCase import MpfTestCase
import mpf.platforms.pololu_maestro


class TestPololuMaestro(MpfTestCase):

    def getConfigFile(self):
        return 'pololu_maestro.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/pololu_maestro/'

    def get_platform(self):
        return 'pololu_maestro'

    def setUp(self):
        mpf.platforms.pololu_maestro.serial = MagicMock()
        super().setUp()

    def test_servo_go_to_position(self):
        # full range servo
        self.machine.default_platform.servo_go_to_position = MagicMock()
        gtp = self.machine.default_platform.servo_go_to_position
        # go to position 1.0 (on of the ends)
        self.machine.servos.servo1.go_to_position(1.0)
        # assert that platform got called
        gtp.assert_called_with(1, 9000.0)
        # go to position 0.0 (other end)
        self.machine.servos.servo1.go_to_position(0.0)
        # assert that platform got called
        gtp.assert_called_with(1, 3000.0)

        gtp.reset_mock()
        # go to position 1.0 (on of the ends)
        self.machine.servos.servo2.go_to_position(1.0)
        # assert that platform got called
        gtp.assert_called_with(2, 10000.0)
        # go to position 0.0 (other end)
        self.machine.servos.servo2.go_to_position(0.0)
        # assert that platform got called
        gtp.assert_called_with(2, 0.0)
        # go to position 0.0 (middle)
        self.machine.servos.servo2.go_to_position(0.5)
        # assert that platform got called
        gtp.assert_called_with(2, 5000.0)

    def test_events(self):

        self.machine.hardware_platforms['pololu_maestro']. \
            servo_go_to_position = MagicMock()
        gtp = (self.machine.hardware_platforms['pololu_maestro'].
               servo_go_to_position)

        self.post_event("reset_servo1")
        gtp.assert_called_with(1, 6000.0)

        self.post_event("servo1_down")
        gtp.assert_called_with(1, 3600.0)

        self.post_event("servo1_up")
        gtp.assert_called_with(1, 8400.0)

        self.post_event("reset_servo2")
        gtp.assert_called_with(2, 10000.0)

        self.post_event("servo2_left")
        gtp.assert_called_with(2, 2000.0)

        self.post_event("servo2_home")
        gtp.assert_called_with(2, 10000.0)
