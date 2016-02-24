from mpf.tests.MpfTestCase import MpfTestCase


class TestMultiBall(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/multiball/'

    def get_platform(self):
        return 'smart_virtual'

    def testSimpleMultiball(self):
        self.mock_event("multiball_mb1_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        self.assertFalse(self.machine.multiballs.mb1.enabled)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        # mb1 should not start because its not enabled
        self.post_event("mb1_start")
        self.assertEqual(0, self.machine.multiballs.mb1.balls_ejected)
        self.assertFalse(self.machine.multiballs.mb1.enabled)

        self.post_event("mb1_enable")

        # multiball should be enabled now but not started
        self.assertTrue(self.machine.multiballs.mb1.enabled)
        self.assertEqual(0, self.machine.multiballs.mb1.balls_ejected)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # ball drains right away
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # multiball not started. game should end
        self.assertEqual(None, self.machine.game)

        # start game again
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()
        self.post_event("mb1_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb1.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb1_start")
        self.assertEqual(1, self.machine.multiballs.mb1.balls_ejected)

        # another ball should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # it should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # two balls drain
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events['multiball_mb1_ended'])

        # they should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(2, self.machine.playfield.balls)

        # shoot again ends
        self.advance_time_and_run(10)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # mb ends
        self.assertEqual(1, self._events['multiball_mb1_ended'])

        # the other ball also drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testUnlimitedShootAgain(self):
        self.mock_event("multiball_mb2_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        self.post_event("mb2_enable")

        # multiball should be enabled
        self.assertTrue(self.machine.multiballs.mb2.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb2_start")
        self.assertEqual(2, self.machine.multiballs.mb2.balls_ejected)

        # another two balls should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.playfield.balls)

        # it should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # two balls drain
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self._events['multiball_mb2_ended'])

        # they should be readded because of shoot again
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # shoot again forever
        self.advance_time_and_run(100)

        # three balls drain
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.playfield.balls)

        # they should be readded because of shoot again
        self.advance_time_and_run(20)
        self.assertEqual(3, self.machine.playfield.balls)

        # end mb
        self.post_event("mb2_stop")

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # mb does not end yet
        self.assertEqual(0, self._events['multiball_mb2_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        # mb ends
        self.assertEqual(1, self._events['multiball_mb2_ended'])

        # the other ball also drains
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

    def testSimultaneousMultiballs(self):
        self.mock_event("multiball_mb2_ended")
        self.mock_event("multiball_mb3_ended")

        # prepare game
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)
        self.machine.switch_controller.process_switch('s_ball_switch5', 1)
        self.machine.switch_controller.process_switch('s_ball_switch6', 1)

        self.advance_time_and_run(10)
        self.assertEqual(6, self.machine.ball_controller.num_balls_known)
        self.assertEqual(6, self.machine.ball_devices.bd_trough.balls)

        # start game
        self.machine.switch_controller.process_switch('s_start', 1)
        self.machine.switch_controller.process_switch('s_start', 0)
        self.machine_run()

        self.post_event("mb2_enable")
        self.post_event("mb3_enable")

        # multiballs should be enabled
        self.assertTrue(self.machine.multiballs.mb2.enabled)
        self.assertTrue(self.machine.multiballs.mb3.enabled)

        # takes roughly 4s to get ball confirmed
        self.advance_time_and_run(4)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)

        # mb started
        self.post_event("mb2_start")
        self.assertEqual(2, self.machine.multiballs.mb2.balls_ejected)

        # another two balls should be ejected to pf
        self.advance_time_and_run(10)
        self.assertEqual(3, self.machine.playfield.balls)

        # start mb3
        self.post_event("mb3_start")
        self.assertEqual(1, self.machine.multiballs.mb3.balls_ejected)

        # another ball should appear
        self.advance_time_and_run(10)
        self.assertEqual(4, self.machine.playfield.balls)

        self.assertTrue(self.machine.multiballs.mb2.shoot_again)
        self.assertFalse(self.machine.multiballs.mb3.shoot_again)

        self.post_event("mb2_stop")
        self.assertFalse(self.machine.multiballs.mb2.shoot_again)

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch1', 1)
        self.advance_time_and_run(1)

        # game should not end
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(3, self.machine.playfield.balls)
        self.assertEqual(0, self._events['multiball_mb2_ended'])
        self.assertEqual(1, self._events['multiball_mb3_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch2', 1)
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(2, self.machine.playfield.balls)
        self.assertEqual(0, self._events['multiball_mb2_ended'])
        self.assertEqual(1, self._events['multiball_mb3_ended'])

        # ball drains
        self.machine.switch_controller.process_switch('s_ball_switch3', 1)
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, self._events['multiball_mb2_ended'])
        self.assertEqual(1, self._events['multiball_mb3_ended'])

        # last ball drains
        self.machine.switch_controller.process_switch('s_ball_switch4', 1)

        # game should end
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)
