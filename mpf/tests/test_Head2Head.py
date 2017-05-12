from mpf.tests.MpfTestCase import MpfTestCase


class TestHead2Head(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/head2head/'

    def get_platform(self):
        return 'smart_virtual'

    def _prepare_troughs(self):
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_front)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_front)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_front)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_back)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_back)
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_back)

        self.advance_time_and_run()

        self.assertEqual(3, self.machine.ball_devices.bd_trough_front.balls)
        self.assertEqual(3, self.machine.ball_devices.bd_trough_back.balls)
        self.assertEqual(0, self.machine.playfields.playfield_front.balls)
        self.assertEqual(0, self.machine.playfields.playfield_back.balls)

    def test_loop(self):
        self._prepare_troughs()
        self.machine.ball_devices.bd_trough_front.eject(target=self.machine.ball_devices.bd_trough_back)
        self.machine.ball_devices.bd_trough_back.eject(target=self.machine.ball_devices.bd_trough_front)
        self.machine.ball_devices.bd_trough_front.eject(target=self.machine.ball_devices.bd_trough_back)
        self.machine.ball_devices.bd_trough_back.eject(target=self.machine.ball_devices.bd_trough_front)

        self.advance_time_and_run(100)

        self.assertEqual("idle", self.machine.ball_devices.bd_trough_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_trough_back._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_launcher_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_launcher_back._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_feeder_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_feeder_back._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_middle_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_middle_back._state)

        self.assertEqual(3, self.machine.ball_devices.bd_trough_front.balls)
        self.assertEqual(3, self.machine.ball_devices.bd_trough_back.balls)
        self.assertEqual(0, self.machine.playfields.playfield_front.balls)
        self.assertEqual(0, self.machine.playfields.playfield_back.balls)

    def testEject(self):
        self._prepare_troughs()
        self.machine.playfields.playfield_front.add_ball()
        self.machine.playfields.playfield_back.add_ball()

        self.assertEqual(2, self.machine.ball_devices.bd_trough_front.available_balls)
        self.assertEqual(2, self.machine.ball_devices.bd_trough_back.available_balls)
        self.assertEqual(1, self.machine.playfields.playfield_front.available_balls)
        self.assertEqual(1, self.machine.playfields.playfield_back.available_balls)
        self.assertEqual(3, self.machine.ball_devices.bd_trough_front.balls)
        self.assertEqual(3, self.machine.ball_devices.bd_trough_back.balls)
        self.assertEqual(0, self.machine.playfields.playfield_front.balls)
        self.assertEqual(0, self.machine.playfields.playfield_back.balls)

        self.advance_time_and_run(10)

        self.assertEqual(2, self.machine.ball_devices.bd_trough_front.balls)
        self.assertEqual(2, self.machine.ball_devices.bd_trough_back.balls)
        self.assertEqual(1, self.machine.playfields.playfield_front.balls)
        self.assertEqual(1, self.machine.playfields.playfield_back.balls)

        self.assertEqual("idle", self.machine.ball_devices.bd_trough_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_trough_back._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_launcher_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_launcher_back._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_feeder_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_feeder_back._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_middle_front._state)
        self.assertEqual("idle", self.machine.ball_devices.bd_middle_back._state)

    def testUnexpectedBallWithTransfer(self):
        # devices captures from one pf and ejects to another
        # tests target_on_unexpected_ball
        self.set_num_balls_known(4)
        self.machine.playfields.playfield_front.balls = 2
        self.machine.playfields.playfield_front.available_balls = 2
        self.machine.playfields.playfield_back.balls = 2
        self.machine.playfields.playfield_back.available_balls = 2

        self.hit_switch_and_run("s_middle_back1", 15)

        self.assertEqual(1, self.machine.playfields.playfield_front.balls)
        self.assertEqual(1, self.machine.playfields.playfield_front.available_balls)
        self.assertEqual(3, self.machine.playfields.playfield_back.balls)
        self.assertEqual(3, self.machine.playfields.playfield_back.available_balls)

    def testUnexpectedBallWithRouting(self):
        # device captures and ejects to same pf but ball has to routed through trough
        self.set_num_balls_known(4)
        self.machine.playfields.playfield_front.balls = 2
        self.machine.playfields.playfield_front.available_balls = 2
        self.machine.playfields.playfield_back.balls = 2
        self.machine.playfields.playfield_back.available_balls = 2

        self.hit_switch_and_run("s_launcher_lane_front", 1)

        # ball captured
        self.assertEqual(1, self.machine.playfields.playfield_front.balls)
        self.assertEqual(2, self.machine.playfields.playfield_back.balls)

        self.advance_time_and_run(20)
        self.assertEqual(2, self.machine.playfields.playfield_front.balls)
        self.assertEqual(2, self.machine.playfields.playfield_back.balls)

    def testPhantomballsAndGameStart(self):
        self.mock_event("playfield_jump")
        self._prepare_troughs()
        self.machine.playfields.playfield_front.add_ball()
        self.machine.playfields.playfield_back.add_ball()
        self.advance_time_and_run(10)

        # test pass from pf1 to pf2 but switch triggers twice
        pf1 = self.machine.ball_devices['playfield_front']
        pf2 = self.machine.ball_devices['playfield_back']

        self.assertEqual(1, pf1.balls)
        self.assertEqual(1, pf1.available_balls)
        self.assertEqual(1, pf2.balls)
        self.assertEqual(1, pf2.available_balls)

        # game should not start. there are balls on pf
        self.assertFalse(self.machine.ball_controller.request_to_start_game())

        self.machine.switch_controller.process_switch("s_transfer_front_back", 1)
        self.advance_time_and_run(2)

        self.assertEqual(0, pf1.balls)
        self.assertEqual(0, pf1.available_balls)
        self.assertEqual(2, pf2.balls)
        self.assertEqual(2, pf2.available_balls)

        self.machine.switch_controller.process_switch("s_transfer_front_back", 1)
        self.advance_time_and_run(2)

        self.assertEqual(0, pf1.balls)
        self.assertEqual(0, pf1.available_balls)
        self.assertEqual(2, pf2.balls)
        self.assertEqual(2, pf2.available_balls)

        # ball drains in front
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_front)
        self.advance_time_and_run()

        self.assertEqual(0, pf1.balls)
        self.assertEqual(0, pf1.available_balls)
        self.assertEqual(1, pf2.balls)
        self.assertEqual(1, pf2.available_balls)

        # from the machine perspective one ball jumped from back to front
        self.assertEventCalledWith("playfield_jump", source=pf2, target=pf1)
        self.assertEventCalled("playfield_jump", 1)
        self.mock_event("playfield_jump")

        self.assertFalse(self.machine.ball_controller.request_to_start_game())

        # second ball also drains
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.bd_trough_back)
        self.advance_time_and_run()

        self.assertEqual(0, pf1.balls)
        self.assertEqual(0, pf1.available_balls)
        self.assertEqual(0, pf2.balls)
        self.assertEqual(0, pf2.available_balls)

        # game should start
        self.assertTrue(self.machine.ball_controller.request_to_start_game())
        self.assertEventNotCalled("playfield_jump")

    def testPlayfieldJump(self):
        self.mock_event("playfield_jump")
        self._prepare_troughs()
        self.machine.playfields.playfield_front.add_ball()
        self.advance_time_and_run(10)

        # only front has a ball
        pf1 = self.machine.ball_devices['playfield_front']
        pf2 = self.machine.ball_devices['playfield_back']

        self.assertEqual(1, pf1.balls)
        self.assertEqual(1, pf1.available_balls)
        self.assertEqual(0, pf2.balls)
        self.assertEqual(0, pf2.available_balls)

        # balls jumps to back pf and falls into a device
        self.hit_switch_and_run("s_feeder_back", 5)

        self.assertEqual(0, pf1.balls)
        self.assertEqual(0, pf1.available_balls)
        self.assertEqual(1, pf2.balls)
        self.assertEqual(1, pf2.available_balls)

        self.assertEventCalledWith("playfield_jump", source=pf1, target=pf2)
