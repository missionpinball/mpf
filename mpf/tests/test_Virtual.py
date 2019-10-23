from mpf.tests.MpfTestCase import MpfTestCase


class TestSmartVirtualPlatform(MpfTestCase):

    def get_config_file(self):
        return "test_virtual.yaml"

    def get_machine_path(self):
        return 'tests/machine_files/platform/'

    def test_load_config_and_allow_enable(self):
        # test that we can load the config with coil and switch parameters from platforms

        self.machine.coils["c_test_allow_enable"].enable()
        self.machine.coils["c_test_hold_power"].enable()

        with self.assertRaises(AssertionError):
            self.machine.coils["c_test_no_allow_enable"].enable()
