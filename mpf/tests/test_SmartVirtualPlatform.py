from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestSmartVirtualPlatform(MpfTestCase):

    def getConfigFile(self):
        if self._testMethodName == "test_eject":
            return "test_smart_virtual_initial.yaml"
        else:
            return 'test_smart_virtual.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/smart_virtual_platform/'

    def get_platform(self):
        return 'smart_virtual'

    def test_eject(self):
        # device1_s1 is active in this test initially
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
