from mpf.tests.MpfTestCase import MpfTestCase


class TestSmartVirtualPlatform(MpfTestCase):

    def getConfigFile(self):
        if self._testMethodName in ["test_eject", "test_eject_with_plunger"]:
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
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(True, self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s2'))

        self.machine.ball_devices.device1.eject()
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices.device1.balls)
        self.assertEqual(1, self.machine.ball_devices.device2.balls)

        self.assertEqual(True, self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s2'))

    def test_eject_with_plunger(self):
        self.machine.ball_devices.device1.config['mechanical_eject'] = True
        self.machine.ball_devices.device1.config['eject_coil'] = None

        self.assertEqual(1, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(True, self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s2'))

        self.machine.ball_devices.device1.setup_player_controlled_eject(target=self.machine.ball_devices.device2)
        self.advance_time_and_run(1)

        self.assertEqual(1, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(True, self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s2'))

        self.advance_time_and_run(3)

        self.assertEqual(0, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s2'))

    def test_eject_with_no_ball(self):
        # tests that firing a coil of a device with no balls in it does not
        # put a ball in the target device.
        self.assertEqual(0, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s2'))

        self.machine.coils.plunger.pulse()
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices.device1.balls)
        self.assertEqual(0, self.machine.ball_devices.device2.balls)
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device2_s2'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s1'))
        self.assertEqual(False, self.machine.switch_controller.is_active('device1_s2'))

    def test_start_active_switches(self):
        # tests that the virtual_platform_start_active_switches really do start
        # active.
        self.assertEqual(3, self.machine.ball_devices.trough.balls)

    def test_drop_targets(self):
        # complete target
        self.assertFalse(self.machine.drop_targets['left3'].complete)
        self.hit_switch_and_run("switch3", 1)
        self.assertTrue(self.machine.drop_targets['left3'].complete)

        # reset target
        self.machine.drop_targets['left3'].reset()
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active('switch3'))
        self.assertFalse(self.machine.drop_targets['left3'].complete)

        # knockdown single target
        self.machine.drop_targets['left3'].knockdown()
        self.advance_time_and_run()
        self.assertTrue(self.machine.switch_controller.is_active('switch3'))
        self.assertTrue(self.machine.drop_targets['left3'].complete)

        # test bank
        self.assertFalse(self.machine.drop_targets['left1'].complete)
        self.assertFalse(self.machine.drop_targets['left2'].complete)
        self.assertFalse(self.machine.drop_target_banks['left_bank'].complete)

        self.hit_switch_and_run("switch1", .1)
        self.hit_switch_and_run("switch2", .1)
        self.assertTrue(self.machine.drop_targets['left1'].complete)
        self.assertTrue(self.machine.drop_targets['left2'].complete)
        self.assertTrue(self.machine.drop_target_banks['left_bank'].complete)

        # it should reset after 1s
        self.advance_time_and_run()
        self.assertFalse(self.machine.switch_controller.is_active('switch1'))
        self.assertFalse(self.machine.switch_controller.is_active('switch2'))
        self.assertFalse(self.machine.drop_targets['left1'].complete)
        self.assertFalse(self.machine.drop_targets['left2'].complete)
        self.assertFalse(self.machine.drop_target_banks['left_bank'].complete)


