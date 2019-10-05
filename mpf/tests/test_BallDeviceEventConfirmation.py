import mpf.tests.test_BallDeviceSwitchConfirmation


class TestBallDeviceEventConfirmation(
    mpf.tests.test_BallDeviceSwitchConfirmation
        .TestBallDeviceSwitchConfirmation):

    def get_config_file(self):
        return 'test_ball_device_event_confirmation.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def _hit_confirm(self):
        self.machine.events.post("launcher_confirm")
