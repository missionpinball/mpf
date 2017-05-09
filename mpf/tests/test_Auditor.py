from mpf.plugins.auditor import Auditor
from mpf.tests.MpfTestCase import MpfTestCase


class TestAuditor(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def get_platform(self):
        return 'smart_virtual'

    def getMachinePath(self):
        return 'tests/machine_files/auditor/'

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.auditor.Auditor']
        super().setUp()

    def test_auditor_switches(self):
        self.machine.ball_controller.num_balls_known = 1
        self.machine.playfield.available_balls = 1
        self.machine.playfield.balls = 1

        auditor = self.machine.plugins[0]
        self.assertIsInstance(auditor, Auditor)
        self.machine.switch_controller.process_switch("s_ball", 1)

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(1)

        self.assertEqual(0, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(0, "audits_switches_s_test")

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(100)

        # there should be a game
        self.assertNotEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball", 1)
        self.advance_time_and_run(100)

        self.assertEqual(None, self.machine.game)

        self.assertEqual(1, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(1, "audits_switches_s_test")

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(1, "audits_switches_s_test")

        auditor.enable()

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(1)

        self.assertEqual(2, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(2, "audits_switches_s_test")

        # should not crash on unknown switch
        self.machine.switch_controller.process_switch_by_num(123123123123, 1, self.machine.default_platform)
        self.advance_time_and_run()

        auditor.disable()

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(1)

        self.assertEqual(2, auditor.current_audits['switches']['s_test'])
