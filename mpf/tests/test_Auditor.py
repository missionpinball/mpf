from mpf.plugins.auditor import Auditor
from mpf.tests.MpfTestCase import MpfTestCase


class TestAuditor(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_platform(self):
        return 'smart_virtual'

    def get_machine_path(self):
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
        data_manager = auditor.data_manager
        self.machine.switch_controller.process_switch("s_ball", 1)

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(2)

        self.assertEqual(0, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(0, "audits_switches_s_test")

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(10)

        # there should be a game
        self.assertNotEqual(None, self.machine.game)

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball", 1)
        self.advance_time_and_run(2)

        self.assertEqual(None, self.machine.game)

        self.assertEqual(1, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(1, "audits_switches_s_test")

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(1, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(1, "audits_switches_s_test")
        self.assertEqual(1, data_manager.written_data['switches']['s_test'])

        auditor.enable()

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(2, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(2, "audits_switches_s_test")
        self.assertEqual(2, data_manager.written_data['switches']['s_test'])

        self.post_event("test_event1")
        self.post_event("test_event2")
        self.post_event("test_event3")
        self.advance_time_and_run(.1)

        self.assertMachineVarEqual(2, "audits_switches_s_test")
        self.assertEqual(1, data_manager.written_data['events']['test_event1'])
        self.assertEqual(1, data_manager.written_data['events']['test_event2'])
        self.assertNotIn("test_event3", data_manager.written_data['events'])

        self.post_event("test_event1")
        self.advance_time_and_run(.1)

        self.assertEqual(2, data_manager.written_data['events']['test_event1'])
        self.assertEqual(1, data_manager.written_data['events']['test_event2'])

        # should not crash on unknown switch
        self.machine.switch_controller.process_switch_by_num(123123123123, 1, self.machine.default_platform)
        self.advance_time_and_run(.1)

        auditor.disable()

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(2, auditor.current_audits['switches']['s_test'])
        self.assertEqual(2, data_manager.written_data['switches']['s_test'])

        self.post_event("auditor_reset")
        self.advance_time_and_run(.1)

        self.assertEqual(0, auditor.current_audits['switches']['s_test'])
        self.assertEqual(0, data_manager.written_data['switches']['s_test'])
