from mpf.tests.MpfTestCase import MpfTestCase


class TestSmartVirtualPlatform(MpfTestCase):

    def getConfigFile(self):
        if self._testMethodName in ["test_eject", "test_eject_with_plunger"]:
            return "test_smart_virtual_initial.yaml"
        elif self._testMethodName == 'test_coil_fired_plunger':
            return "test_coil_fired_plunger.yaml"
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
        trough = self.machine.ball_devices.trough2
        plunger = self.machine.ball_devices.plunger2

        # add two balls to trough
        self.machine.default_platform.add_ball_to_device(trough)
        self.machine.default_platform.add_ball_to_device(trough)
        self.advance_time_and_run()

        self.assertEqual(2, trough.balls)
        self.assertEqual(0, plunger.balls)
        self.assertBallsOnPlayfield(0)
        self.assertTrue(self.machine.switch_controller.is_active('trough2_1'))
        self.assertTrue(self.machine.switch_controller.is_active('trough2_2'))
        self.assertFalse(self.machine.switch_controller.is_active('trough2_3'))
        self.assertFalse(self.machine.switch_controller.is_active('plunger2'))

        self.machine.playfield.add_ball(1, plunger)
        self.advance_time_and_run(1)

        self.assertEqual(1, trough.balls)
        self.assertEqual(1, plunger.balls)
        self.assertBallsOnPlayfield(0)
        self.assertFalse(self.machine.switch_controller.is_active('trough2_1'))
        self.assertTrue(self.machine.switch_controller.is_active('trough2_2'))
        self.assertFalse(self.machine.switch_controller.is_active('trough2_3'))
        self.assertTrue(self.machine.switch_controller.is_active('plunger2'))

        self.advance_time_and_run(3)
        self.assertEqual(1, trough.balls)
        self.assertEqual(0, plunger.balls)
        self.assertBallsOnPlayfield(0)
        self.assertFalse(self.machine.switch_controller.is_active('trough2_1'))
        self.assertTrue(self.machine.switch_controller.is_active('trough2_2'))
        self.assertFalse(self.machine.switch_controller.is_active('trough2_3'))
        self.assertFalse(self.machine.switch_controller.is_active('plunger2'))

        self.advance_time_and_run(10)
        self.assertEqual(1, trough.balls)
        self.assertEqual(0, plunger.balls)
        self.assertBallsOnPlayfield(1)
        self.assertFalse(self.machine.switch_controller.is_active('trough2_1'))
        self.assertTrue(self.machine.switch_controller.is_active('trough2_2'))
        self.assertFalse(self.machine.switch_controller.is_active('trough2_3'))
        self.assertFalse(self.machine.switch_controller.is_active('plunger2'))

    def _ball_swallower(self, unclaimed_balls, **kwargs):
        return {'unclaimed_balls': 0}

    def test_ball_device_with_entrance_switch(self):
        self.machine.events.add_handler('balldevice_device3_ball_enter',
                                        self._ball_swallower)

        self.assertEqual(0, self.machine.ball_devices.device3.balls)
        self.advance_time_and_run(1)

        self.hit_and_release_switch('device3_s')
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.ball_devices.device3.balls)

        self.hit_and_release_switch('device3_s')
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.ball_devices.device3.balls)

        self.hit_and_release_switch('device3_s')
        self.advance_time_and_run()
        self.assertEqual(3, self.machine.ball_devices.device3.balls)

        self.machine.ball_devices.device3.eject()
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.ball_devices.device3.balls)

    def test_ball_device_with_entrance_switch_full_timeout(self):
        self.machine.events.add_handler('balldevice_device4_ball_enter',
                                        self._ball_swallower)

        self.assertEqual(0, self.machine.ball_devices.device4.balls)
        self.advance_time_and_run(1)

        self.hit_and_release_switch('device4_s')
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.ball_devices.device4.balls)

        self.hit_and_release_switch('device4_s')
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.ball_devices.device4.balls)

        self.hit_switch_and_run('device4_s', 1)
        self.assertEqual(3, self.machine.ball_devices.device4.balls)

        self.machine.playfield.add_ball(1, self.machine.ball_devices.device4)
        self.advance_time_and_run(3)
        self.hit_switch_and_run('playfield', 1)

        self.assertEqual(2, self.machine.ball_devices.device4.balls)
        self.assertFalse(self.machine.switch_controller.is_active('device4_s'))

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

        # it should reset after 1.5s
        self.advance_time_and_run(1.5)
        self.assertFalse(self.machine.switch_controller.is_active('switch1'))
        self.assertFalse(self.machine.switch_controller.is_active('switch2'))
        self.assertFalse(self.machine.drop_targets['left1'].complete)
        self.assertFalse(self.machine.drop_targets['left2'].complete)
        self.assertFalse(self.machine.drop_target_banks['left_bank'].complete)

    def test_coil_fired_plunger(self):
        self.advance_time_and_run(2)
        self.assertEqual(5, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.shooter_lane.balls)
        self.assertEqual(0, self.machine.playfield.balls)

        self.hit_and_release_switch('s_start')
        self.assertModeRunning('game')
        self.advance_time_and_run(3)

        self.assertEqual(4, self.machine.ball_devices.trough.balls)
        self.assertEqual(1, self.machine.ball_devices.shooter_lane.balls)
        self.assertEqual(0, self.machine.playfield.balls)

        self.hit_and_release_switch('s_shooter_lane')
        self.advance_time_and_run()

        self.assertEqual(4, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.shooter_lane.balls)
        self.assertEqual(0, self.machine.playfield.balls)

        self.hit_and_release_switch('s_standup')
        self.advance_time_and_run()

        self.assertEqual(4, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.shooter_lane.balls)
        self.assertEqual(1, self.machine.playfield.balls)