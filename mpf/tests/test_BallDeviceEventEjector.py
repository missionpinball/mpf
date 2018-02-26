from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestBallDeviceEventEjector(MpfGameTestCase):

    def getConfigFile(self):
        return 'test_ball_device_event_ejector.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def testEject(self):
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.hit_switch_and_run("s_ball_switch2", 1)

        self.mock_event("trough_eject")
        self.machine.playfield.add_ball(1)
        self.advance_time_and_run()
        self.assertEventCalled("trough_eject")
