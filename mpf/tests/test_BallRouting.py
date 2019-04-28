from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestBallRouting(MpfGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_routing/'

    def get_platform(self):
        return 'smart_virtual'

    def test_routing(self):
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.start_game()
        self.advance_time_and_run(10)

        self.assertBallsOnPlayfield(1)

        # by default the ball is routed back to the playfield
        self.mock_event("balldevice_test_device1_ball_enter")
        self.mock_event("balldevice_test_device2_ball_enter")
        self.hit_switch_and_run("s_device1", 1)
        self.assertBallsOnPlayfield(0)
        self.assertAvailableBallsOnPlayfield(1)
        self.advance_time_and_run(20)
        self.assertBallsOnPlayfield(1)
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEventCalledWith("balldevice_test_device1_ball_enter",
                                   device=self.machine.ball_devices["test_device1"], new_balls=1, unclaimed_balls=1,
                                   new_available_balls=1)
        self.assertEventCalledWith("balldevice_test_device2_ball_enter",
                                   device=self.machine.ball_devices["test_device2"], new_balls=1, unclaimed_balls=0,
                                   new_available_balls=0)

        self.start_mode("mode1")
        # route ball via device2
        self.post_event("route_to_2")
        self.mock_event("balldevice_test_device1_ball_enter")
        self.mock_event("balldevice_test_device2_ball_enter")
        self.mock_event("balldevice_test_device3_ball_enter")
        self.mock_event("balldevice_test_device4_ball_enter")
        self.hit_switch_and_run("s_device1", 1)
        self.assertBallsOnPlayfield(0)
        self.advance_time_and_run(20)
        self.assertBallsOnPlayfield(1)
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEventCalledWith("balldevice_test_device1_ball_enter",
                                   device=self.machine.ball_devices["test_device1"], new_balls=1, unclaimed_balls=0,
                                   new_available_balls=1)
        self.assertEventCalledWith("balldevice_test_device2_ball_enter",
                                   device=self.machine.ball_devices["test_device2"], new_balls=1, unclaimed_balls=1,
                                   new_available_balls=0)
        self.assertEventNotCalled("balldevice_test_device3_ball_enter")
        self.assertEventNotCalled("balldevice_test_device4_ball_enter")

        # route ball via device4
        self.post_event("route_to_4")
        self.mock_event("balldevice_test_device1_ball_enter")
        self.mock_event("balldevice_test_device2_ball_enter")
        self.mock_event("balldevice_test_device3_ball_enter")
        self.mock_event("balldevice_test_device4_ball_enter")
        self.hit_switch_and_run("s_device1", 1)
        self.assertBallsOnPlayfield(0)
        self.advance_time_and_run(20)
        self.assertBallsOnPlayfield(1)
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEventCalledWith("balldevice_test_device1_ball_enter",
                                   device=self.machine.ball_devices["test_device1"], new_balls=1, unclaimed_balls=0,
                                   new_available_balls=1)
        self.assertEventNotCalled("balldevice_test_device2_ball_enter")
        self.assertEventCalledWith("balldevice_test_device3_ball_enter",
                                   device=self.machine.ball_devices["test_device3"], new_balls=1, unclaimed_balls=0,
                                   new_available_balls=0)
        self.assertEventCalledWith("balldevice_test_device4_ball_enter",
                                   device=self.machine.ball_devices["test_device4"], new_balls=1, unclaimed_balls=1,
                                   new_available_balls=0)
        self.assertEqual(0, self.machine.ball_devices["test_device4"].balls)
        self.assertEqual(0, self.machine.ball_devices["test_device4"].available_balls)

        # route ball to device4 and lock it
        self.post_event("lock_enable")
        self.post_event("route_to_4")
        self.mock_event("balldevice_test_device1_ball_enter")
        self.mock_event("balldevice_test_device2_ball_enter")
        self.mock_event("balldevice_test_device3_ball_enter")
        self.mock_event("balldevice_test_device4_ball_enter")
        self.hit_switch_and_run("s_device1", 1)
        self.assertBallsOnPlayfield(0)
        self.advance_time_and_run(20)
        self.assertBallsOnPlayfield(1)
        self.assertAvailableBallsOnPlayfield(1)
        self.assertEventCalledWith("balldevice_test_device1_ball_enter",
                                   device=self.machine.ball_devices["test_device1"], new_balls=1, unclaimed_balls=0,
                                   new_available_balls=1)
        self.assertEventNotCalled("balldevice_test_device2_ball_enter")
        self.assertEventCalledWith("balldevice_test_device3_ball_enter",
                                   device=self.machine.ball_devices["test_device3"], new_balls=1, unclaimed_balls=0,
                                   new_available_balls=0)
        self.assertEventCalledWith("balldevice_test_device4_ball_enter",
                                   device=self.machine.ball_devices["test_device4"], new_balls=1, unclaimed_balls=0,
                                   new_available_balls=0)
        self.assertEqual(1, self.machine.ball_devices["test_device4"].balls)
        self.assertEqual(1, self.machine.ball_devices["test_device4"].available_balls)
