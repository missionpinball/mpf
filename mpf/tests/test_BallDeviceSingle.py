from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestBallDeviceSingle(MpfGameTestCase):

    def get_platform(self):
        return "smart_virtual"

    def getConfigFile(self):
        return 'test_single_device.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def testEjectAndDrain(self):
        # start game
        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

        self.start_game()
        self.assertPlayerNumber(1)
        self.assertBallNumber(1)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.playfield.available_balls)

        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices.trough)
        self.advance_time_and_run()
        self.assertEqual(0, self.machine.playfield.balls)
        self.assertEqual(1, self.machine.playfield.available_balls)

        self.assertPlayerNumber(1)
        self.assertBallNumber(2)
        self.advance_time_and_run(10.5)
        self.assertEqual(1, self.machine.playfield.available_balls)
        self.assertEqual(1, self.machine.playfield.balls)
