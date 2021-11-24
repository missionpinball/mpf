from mpf.plugins.auditor import Auditor
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestAuditor(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_platform(self):
        return 'smart_virtual'

    def get_machine_path(self):
        return 'tests/machine_files/auditor/'

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.auditor.Auditor']
        super().setUp()

    def test_auditor_player_vars(self):
        auditor = self.machine.plugins[0]
        self.assertIsInstance(auditor, Auditor)
        data_manager = auditor.data_manager

        # start a game
        self.start_game()

        self.post_event("add_score")
        self.post_event("add_custom")
        self.post_event("add_custom")
        self.post_event("add_not_audited")
        self.assertPlayerVarEqual(100, "score")

        self.drain_all_balls()
        self.assertGameIsNotRunning()

        self.assertEqual(100, auditor.current_audits['player']['score']['average'])
        self.assertEqual([100], auditor.current_audits['player']['score']['top'])
        self.assertEqual(1, auditor.current_audits['player']['score']['total'])
        self.assertEqual(200, auditor.current_audits['player']['my_var']['average'])
        self.assertEqual([200], auditor.current_audits['player']['my_var']['top'])
        self.assertEqual(1, auditor.current_audits['player']['my_var']['total'])
        self.assertNotIn("not_audited", auditor.current_audits['player'])

        # start a game
        self.start_game()

        self.post_event("add_score")
        self.post_event("add_score")
        self.assertPlayerVarEqual(200, "score")

        self.drain_all_balls()
        self.assertGameIsNotRunning()

        self.assertEqual(150, auditor.current_audits['player']['score']['average'])
        self.assertEqual([200, 100], auditor.current_audits['player']['score']['top'])
        self.assertEqual(2, auditor.current_audits['player']['score']['total'])
        self.assertEqual(100, auditor.current_audits['player']['my_var']['average'])
        self.assertEqual([200, 0], auditor.current_audits['player']['my_var']['top'])
        self.assertEqual(2, auditor.current_audits['player']['my_var']['total'])
        self.assertNotIn("not_audited", auditor.current_audits['player'])

        self.assertEqual({'score': {'top': [200, 100], 'average': 150.0, 'total': 2},
                          'my_var': {'top': [200, 0], 'average': 100.0, 'total': 2}},
                         auditor.data_manager.written_data["player"])

    def test_auditor_switches_events(self):
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
        self.start_game()

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(1)

        self.drain_all_balls()
        self.assertGameIsNotRunning()

        self.assertEqual(1, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(1, "audits_switches_s_test")

        self.machine.switch_controller.process_switch("s_test", 1)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("s_test", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(1, auditor.current_audits['switches']['s_test'])
        self.assertMachineVarEqual(1, "audits_switches_s_test")
        self.assertEqual(1, data_manager.written_data['switches']['s_test'])

        # start a game
        self.start_game()

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

        self.drain_all_balls()
        self.assertGameIsNotRunning()

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
        self.assertEqual(0, auditor.current_audits['events']['game_started'])
        self.assertEqual(0, data_manager.written_data['events']['game_started'])
