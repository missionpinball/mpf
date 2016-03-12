from mpf.tests.MpfTestCase import MpfTestCase

class TestSwitchPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/switch_player/'

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.switch_player.SwitchPlayer']
        super().setUp()

    def _sw_handler(self):
        self.hits += 1

    def test_switch_player(self):
        self.hits = 0
        self.machine.switch_controller.add_switch_handler("s_test3", self._sw_handler)
        self.post_event("test_start")
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.assertEqual(0, self.hits)
        self.advance_time_and_run(0.1)
        self.assertEqual(True, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.advance_time_and_run(0.6)
        self.assertEqual(True, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.assertEqual(1, self.hits)
        self.advance_time_and_run(0.1)
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.assertEqual(1, self.hits)
        self.advance_time_and_run(1)
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(True, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.assertEqual(1, self.hits)
        self.advance_time_and_run(1)
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(True, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.assertEqual(2, self.hits)
        self.advance_time_and_run(0.1)
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.assertEqual(2, self.hits)
        self.advance_time_and_run(1)
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test1"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test2"))
        self.assertEqual(False, self.machine.switch_controller.is_active("s_test3"))
        self.assertEqual(3, self.hits)
