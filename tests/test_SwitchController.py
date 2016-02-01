from tests.MpfTestCase import MpfTestCase


class TestSwitchController(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/switch_controller/'

    def _callback(self):
         self.isActive = self.machine.switch_controller.is_active("s_test", ms=300)

    def test_is_active_timing(self):
        self.isActive = None

        self.machine.switch_controller.add_switch_handler(
                switch_name="s_test",
                callback=self._callback,
                state=1, ms=300)
        self.machine.switch_controller.process_switch("s_test", 1, True)

        self.advance_time_and_run(3)

        self.assertEqual(True, self.isActive)

    def test_initial_state(self):
        # tests that when MPF starts, the initial states of switches that
        # started in that state are read correctly.
        self.assertFalse(self.machine.switch_controller.is_active('s_test',
                                                                  1000))
