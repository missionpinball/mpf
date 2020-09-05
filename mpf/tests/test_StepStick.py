from mpf.tests.MpfTestCase import MpfTestCase, MagicMock


class TestStepStick(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/step_stick/'

    def get_platform(self):
        # no force platform. we are testing step stick
        return False

    def test_step_stick(self):
        direction = self.machine.digital_outputs["c_direction"].hw_driver
        step_enable = self.machine.digital_outputs["c_step"].hw_driver.enable = MagicMock()
        step_disable = self.machine.digital_outputs["c_step"].hw_driver.disable = MagicMock()
        enable = self.machine.digital_outputs["c_enable"].hw_driver
        self.assertEqual("enabled", direction.state)
        self.assertEqual("enabled", enable.state)

        self.advance_time_and_run(1)

        self.assertEqual(25, step_enable.call_count)
        self.assertEqual(25, step_disable.call_count)

        self.hit_switch_and_run("s_home", .1)
        step_enable = self.machine.digital_outputs["c_step"].hw_driver.enable = MagicMock()
        step_disable = self.machine.digital_outputs["c_step"].hw_driver.disable = MagicMock()

        self.advance_time_and_run(1)
        self.assertEqual(0, step_enable.call_count)
        self.assertEqual(0, step_disable.call_count)

        self.post_event("test_01")
        self.advance_time_and_run(1)
        self.assertEqual("enabled", direction.state)
        self.assertEqual(20, step_enable.call_count)
        self.assertEqual(20, step_disable.call_count)

        step_enable = self.machine.digital_outputs["c_step"].hw_driver.enable = MagicMock()
        step_disable = self.machine.digital_outputs["c_step"].hw_driver.disable = MagicMock()
        self.post_event("test_00")
        self.advance_time_and_run(1)
        self.assertEqual("disabled", direction.state)
        self.assertEqual(10, step_enable.call_count)
        self.assertEqual(10, step_disable.call_count)

        step_enable = self.machine.digital_outputs["c_step"].hw_driver.enable = MagicMock()
        step_disable = self.machine.digital_outputs["c_step"].hw_driver.disable = MagicMock()
        self.post_event("test_10")
        self.advance_time_and_run(2)
        self.assertEqual("enabled", direction.state)
        self.assertEqual(40, step_enable.call_count)
        self.assertEqual(40, step_disable.call_count)
