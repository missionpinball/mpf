from mpf.tests.MpfTestCase import MpfTestCase


class TestBallDeviceModernTroughPlungerSetup(MpfTestCase):

    def get_platform(self):
        return "smart_virtual"

    def getConfigFile(self):
        return 'test_modern_trough_plunger_setup.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def test_ball_in_plunger_during_eject(self):
        # add some initial balls
        self.hit_switch_and_run("s_trough_switch1", 0)
        self.hit_switch_and_run("s_trough_switch2", 0)
        self.hit_switch_and_run("s_trough_switch3", 1)
        self.assertNumBallsKnown(3)

        self.machine.playfield.add_ball()
        self.hit_switch_and_run("s_ball_switch_plunger_lane", 0)
        self.advance_time_and_run(100)

        self.assertEqual("idle", self.machine.ball_devices["bd_trough"].state)
        self.assertEqual("idle", self.machine.ball_devices["bd_plunger"].state)
        self.assertBallsOnPlayfield(2)
        self.assertNumBallsKnown(4)
