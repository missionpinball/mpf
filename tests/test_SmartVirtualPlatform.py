from MpfTestCase import MpfTestCase
from mock import MagicMock


class TestSmartVirtualPlatform(MpfTestCase):

    def getConfigFile(self):
        return 'test_smart_virtual.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/platform/'

    def test_eject(self):
        # tests that firing a coil in a ball device with a ball in it
        # successfully activates the right switches to simulate the ball
        # leaving that device and entering the target device.
        self.machine.switch_controller.process_switch('device1_s1', 1)

        # have to stop() it since the ball is unexpected and it will eject it
        # otherwise.
        self.machine.ball_devices.device1.stop()

        self.advance_time_and_run(.6)
        self.assertEqual(1, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(True,
            self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device1_s2'))

        self.machine.coils.device1.pulse()
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices.device1.balls)
        self.assertEqual(1, self.machine.ball_devices.device2.balls)

        self.assertEqual(True,
            self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device1_s2'))

    def test_eject_with_no_ball(self):
        # tests that firing a coil of a device with no balls in it does not
        # put a ball in the target device.
        self.assertEqual(0, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device1_s2'))

        self.machine.coils.plunger.pulse()
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False,
            self.machine.switch_controller.is_active('device1_s2'))

    def test_start_active_switches(self):
        # tests that the virtual_platform_start_active_switches really do start
        # active.
        self.assertEqual(3, self.machine.ball_devices.trough.balls)