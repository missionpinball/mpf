import mpf.tests.test_BallDeviceSwitchConfirmation


class TestBallDeviceEventConfirmation(
    mpf.tests.test_BallDeviceSwitchConfirmation
        .TestBallDeviceSwitchConfirmation):

    def getConfigFile(self):
        return 'test_ball_device_event_confirmation.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def _hit_confirm(self):
        self.machine.events.post("launcher_confirm")
