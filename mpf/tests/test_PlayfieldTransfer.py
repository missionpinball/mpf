from mpf.tests.MpfTestCase import MpfTestCase


class TestPlayfieldTransfer(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/playfield_transfer/'

    def testBallPassThroughSwitch(self):
        # test pass from pf1 to pf2
        pf1 = self.machine.ball_devices['playfield1']
        pf2 = self.machine.ball_devices['playfield2']

        self.set_num_balls_known(4)
        pf1.balls = 2
        pf1.available_balls = 2
        pf2.balls = 2
        pf2.available_balls = 2

        self.machine.switch_controller.process_switch("s_transfer", 1)
        self.advance_time_and_run(2)

        self.assertEqual(1, pf1.balls)
        self.assertEqual(1, pf1.available_balls)
        self.assertEqual(3, pf2.balls)
        self.assertEqual(3, pf2.available_balls)

    def testBallPassThroughEvent(self):
        # test pass from pf1 to pf2
        pf1 = self.machine.ball_devices['playfield1']
        pf2 = self.machine.ball_devices['playfield2']

        self.set_num_balls_known(4)
        pf1.balls = 2
        pf1.available_balls = 2
        pf2.balls = 2
        pf2.available_balls = 2

        self.post_event("transfer_ball")
        self.advance_time_and_run(2)

        self.assertEqual(1, pf1.balls)
        self.assertEqual(1, pf1.available_balls)
        self.assertEqual(3, pf2.balls)
        self.assertEqual(3, pf2.available_balls)
