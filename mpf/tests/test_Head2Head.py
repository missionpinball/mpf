from mpf.tests.MpfTestCase import MpfTestCase


class TestHead2Head(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/head2head/'

    def get_platform(self):
        return 'smart_virtual'

    def testEject(self):
        self.hit_switch_and_run("s_trough1_front", 1)
        self.hit_switch_and_run("s_trough2_front", 1)
        self.hit_switch_and_run("s_trough3_front", 1)
        self.hit_switch_and_run("s_trough1_back", 1)
        self.hit_switch_and_run("s_trough2_back", 1)
        self.hit_switch_and_run("s_trough3_back", 1)

        self.assertEqual(3, self.machine.ball_devices.bd_trough_front.balls)
        self.assertEqual(3, self.machine.ball_devices.bd_trough_back.balls)
        self.assertEqual(0, self.machine.playfields.playfield_front.balls)
        self.assertEqual(0, self.machine.playfields.playfield_back.balls)

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
        self.machine.ball_controller.num_balls_known = 4
        self.machine.playfields.playfield_front.balls = 2
        self.machine.playfields.playfield_back.balls = 2

        self.hit_switch_and_run("s_middle_back1", 15)

        self.assertEqual(1, self.machine.playfields.playfield_front.balls)
        self.assertEqual(3, self.machine.playfields.playfield_back.balls)

    def testUnexpectedBallWithRouting(self):
        # device captures and ejects to same pf but ball has to routed through trough
        self.machine.ball_controller.num_balls_known = 4
        self.machine.playfields.playfield_front.balls = 2
        self.machine.playfields.playfield_back.balls = 2

        self.hit_switch_and_run("s_launcher_lane_front", 1)

        # ball captured
        self.assertEqual(1, self.machine.playfields.playfield_front.balls)
        self.assertEqual(2, self.machine.playfields.playfield_back.balls)

        self.advance_time_and_run(20)
        self.assertEqual(2, self.machine.playfields.playfield_front.balls)
        self.assertEqual(2, self.machine.playfields.playfield_back.balls)