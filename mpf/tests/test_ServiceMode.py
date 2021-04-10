from unittest.mock import MagicMock

from mpf.core.settings_controller import SettingEntry
from mpf.plugins.auditor import Auditor
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestServiceMode(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/service_mode/'

    def setUp(self):
        self.machine_config_patches['mpf']['plugins'] = ['mpf.plugins.auditor.Auditor']
        super().setUp()

    def test_start_stop_service_in_attract(self):
        self.mock_event("service_door_opened")
        self.mock_event("service_door_closed")
        self.mock_event("service_mode_entered")
        self.mock_event("service_mode_exited")

        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertMachineVarEqual(1, "credit_units")
        self.assertModeRunning("attract")

        # open door
        self.hit_switch_and_run("s_door_open", 1)
        self.assertEventCalled('service_door_opened', 1)
        self.assertEventNotCalled('service_door_closed')
        self.assertModeRunning("attract")

        # enter
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalled('service_mode_entered', 1)
        self.assertEventNotCalled('service_mode_exited')
        self.assertModeNotRunning("attract")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertEventCalled('service_mode_entered', 1)
        self.assertEventCalled('service_mode_exited', 1)
        self.assertModeRunning("attract")
        self.assertModeRunning("service")

        # enter again
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalled('service_mode_entered', 2)
        self.assertEventCalled('service_mode_exited', 1)
        self.assertModeNotRunning("attract")

        # close door
        self.release_switch_and_run("s_door_open", 1)
        self.assertEventCalled('service_mode_exited', 1)
        self.assertEventCalled('service_door_closed', 1)
        self.assertModeNotRunning("attract")
        self.assertModeRunning("service")

        # exit service
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertEventCalled('service_mode_exited', 2)
        self.assertEventCalled('service_door_closed', 1)
        self.assertModeRunning("attract")
        self.assertModeRunning("service")
        self.assertModeRunning("credits")

        self.assertMachineVarEqual(1, "credit_units")

        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertMachineVarEqual(2, "credit_units")

    def test_start_stop_service_in_game(self):
        self.assertModeRunning("service")
        self.mock_event("service_door_opened")
        self.mock_event("service_door_closed")
        self.mock_event("service_mode_entered")
        self.mock_event("service_mode_exited")

        # add credit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()

        self.start_game()
        self.assertModeRunning("game")
        self.assertModeRunning("service")
        self.assertSwitchState("s_door_open", 0)

        # open door. game still running
        self.hit_switch_and_run("s_door_open", .1)
        self.assertEventCalled('service_door_opened')
        self.assertEventNotCalled('service_door_closed')
        self.assertModeRunning("game")
        self.assertModeRunning("service")

        # enter service. end game
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalled('service_mode_entered')
        self.assertEventNotCalled('service_mode_exited')
        self.assertModeNotRunning("game")

        # close door. service mode still active
        self.release_switch_and_run("s_door_open", 1)
        self.assertEventCalled('service_door_closed')
        self.assertModeNotRunning("attract")

        # exit service mode
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertModeRunning("attract")
        self.assertEventCalled('service_mode_exited')

    def test_start_menu(self):
        self.mock_event("service_menu_selected")
        # enter menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Diagnostics Menu')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Audits Menu')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Adjustments Menu')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Utilities Menu')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Diagnostics Menu')

        self.hit_and_release_switch("s_service_down")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Utilities Menu')

    def test_utilities_reset(self):
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run(.1)
        self.assertMachineVarEqual(2, "credit_units")
        self.assertEqual({'1 Total Coins service_credit': 2, '2 Total Earnings service_credit': 2},
                         self.machine.modes["credits"].earnings)

        self.start_game()
        self.hit_and_release_switch("s_service_up")
        self.machine.game.player.score = 1000
        self.drain_all_balls()
        self.assertGameIsNotRunning()

        auditor = self.machine.plugins[0]
        self.assertIsInstance(auditor, Auditor)
        self.assertEqual(1, auditor.current_audits['switches']['s_service_up'])
        self.assertTrue(1000, auditor.current_audits['player']['score']['average'])
        self.assertTrue(1, auditor.current_audits['events']['game_ended'])

        self.assertMachineVarEqual(1, "credit_units")

        self.mock_event("service_menu_selected")
        self.mock_event("service_options_slide_start")
        # enter menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Diagnostics Menu')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Audits Menu')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Adjustments Menu')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Utilities Menu')

        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset Menu')

        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset Coin Audits')
        self.assertEventNotCalled("service_options_slide_start")
        self.mock_event("service_menu_selected")
        self.mock_event("service_options_slide_start")

        # RESET earning audits
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_options_slide_start", title="Reset earning audits",
                                   question="Perform coin reset?", option="no", warning="THIS CANNOT BE UNDONE")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_options_slide_start", title="Reset earning audits",
                                   question="Perform coin reset?", option="yes", warning="THIS CANNOT BE UNDONE")
        self.assertEventNotCalled("service_menu_selected")
        self.mock_event("service_options_slide_start")

        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset Coin Audits')
        self.assertEventNotCalled("service_options_slide_start")

        # coins are still there
        self.assertMachineVarEqual(1, "credit_units")
        # but earning audits are reset
        self.assertEqual({}, self.machine.modes["credits"].earnings)

        # RESET game audits
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset Game Audits')
        self.mock_event("service_menu_selected")
        self.mock_event("service_options_slide_start")

        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_options_slide_start", title="Auditor Reset",
                                   question="Reset Game Audits?", option="no", warning="THIS CANNOT BE UNDONE")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_options_slide_start", title="Auditor Reset",
                                   question="Reset Game Audits?", option="yes", warning="THIS CANNOT BE UNDONE")
        self.assertEventNotCalled("service_menu_selected")
        self.mock_event("service_options_slide_start")

        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset Game Audits')
        self.assertEventNotCalled("service_options_slide_start")

        self.assertEqual(0, auditor.current_audits['switches']['s_service_up'])
        self.assertEqual(0, auditor.current_audits['player']['score']['average'])
        self.assertEqual(0, auditor.current_audits['events']['game_ended'])

        # RESET high scores (TEST NOT IMPLEMENTED YET - FEEL FREE)
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset High Scores')
        self.mock_event("service_menu_selected")
        self.mock_event("service_options_slide_start")

        # RESET credits
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset Credits')
        self.mock_event("service_menu_selected")
        self.mock_event("service_options_slide_start")

        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_options_slide_start", title="Reset credits",
                                   question="Remove all credits?", option="no", warning="THIS CANNOT BE UNDONE")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_options_slide_start", title="Reset credits",
                                   question="Remove all credits?", option="yes", warning="THIS CANNOT BE UNDONE")
        self.assertEventNotCalled("service_menu_selected")
        self.mock_event("service_options_slide_start")

        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_menu_selected", label='Reset Credits')
        self.assertEventNotCalled("service_options_slide_start")

        # credits should be gone
        self.assertMachineVarEqual(0, "credit_units")

    def test_switch_test(self):
        self.mock_event("service_menu_selected")
        # enter menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Diagnostics Menu')

        # enter diagnostics menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Switch Menu')

        # enter switch menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Switch Edge Test')

        # start edge test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.mock_event("service_switch_test_start")
        self.mock_event("service_switch_test_stop")
        self.hit_switch_and_run("s_start", 1)

        self.assertEventCalledWith("service_switch_test_start", switch_label='%', switch_name='s_start',
                                   switch_num='', switch_state='active')

        # leave switch test
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertEventCalled("service_switch_test_stop")

    def test_light_test(self):
        self.mock_event("service_menu_selected")
        # enter menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Diagnostics Menu')

        # enter diagnostics menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Switch Menu')

        # select coil menu
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Coil Menu')

        # select light menu
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Light Menu')

        # enter light menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Single Light Test')

        self.mock_event("service_light_test_start")
        self.mock_event("service_light_test_stop")

        # enter single light test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        for color in ["white", "red", "green", "blue", "yellow", "white"]:
            self.assertEventCalledWith("service_light_test_start",
                                       board_name='Virtual',
                                       light_label='%',
                                       light_name='l_light1',
                                       light_num='1',
                                       test_color=color)

            self.assertLightColor("l_light1", color)

            self.hit_and_release_switch("s_service_enter")
            self.advance_time_and_run()

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_light_test_start",
                                   board_name='Virtual',
                                   light_label='%',
                                   light_name='l_light5',
                                   light_num='5',
                                   test_color="red")

        self.assertLightColor("l_light1", "black")
        self.assertLightColor("l_light5", "red")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_light_test_start",
                                   board_name='Virtual',
                                   light_label='%',
                                   light_name='l_light1',
                                   light_num='1',
                                   test_color="red")

        self.assertLightColor("l_light1", "red")
        self.assertLightColor("l_light5", "black")

        # leave switch test
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertEventCalled("service_light_test_stop")

    def test_coil_test(self):
        self.mock_event("service_menu_selected")
        self.mock_event("service_coil_test_start")
        self.mock_event("service_coil_test_stop")
        # enter menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Diagnostics Menu')

        # enter diagnostics menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Switch Menu')

        # select coil menu
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Coil Menu')

        # enter coil menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Single Coil Test')

        # start edge test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        # selects the first coil
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='First coil',
                                   coil_name='c_test', coil_num='1')

        # select test2
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='Second coil',
                                   coil_name='c_test2', coil_num='2')

        self.machine.coils["c_test2"].pulse = MagicMock()
        # pulse it
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.machine.coils["c_test2"].pulse.assert_called_with()

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='Third coil',
                                   coil_name='c_test5', coil_num='3')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='Fourth coil',
                                   coil_name='c_test6', coil_num='10')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='Fifth coil',
                                   coil_name='c_test4', coil_num='100')

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='Sixth coil',
                                   coil_name='c_test3', coil_num='1000')



        # wrap to first
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        # selects the first coil
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='First coil',
                                   coil_name='c_test', coil_num='1')

        # wrap back to last
        self.hit_and_release_switch("s_service_down")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_coil_test_start", board_name='Virtual', coil_label='Sixth coil',
                                   coil_name='c_test3', coil_num='1000')

        # leave coil test
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertEventCalled("service_coil_test_stop")

    def test_volume(self):
        self.mock_event("master_volume_increase")
        self.mock_event("master_volume_decrease")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalled("master_volume_increase", 1)
        self.assertEventCalled("master_volume_decrease", 0)

        self.hit_and_release_switch("s_service_down")
        self.advance_time_and_run()
        self.assertEventCalled("master_volume_increase", 1)
        self.assertEventCalled("master_volume_decrease", 1)

    def test_settings(self):
        self.machine.settings._settings = {}
        self.machine.settings.add_setting(SettingEntry("test1", "Test1", 1, "test1", "b",
                                                       {"a": "A", "b": "B (default)", "c": "C"}, "standard"))
        self.machine.settings.add_setting(SettingEntry("test2", "Test2", 2, "test2", False,
                                                       {True: "Yes", False: "No (default)"}, "standard"))
        self.mock_event("service_settings_start")
        self.mock_event("service_settings_edit")
        self.mock_event("service_settings_stop")

        self.mock_event("service_menu_selected")
        # enter menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Diagnostics Menu')

        # select audits menu
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Audits Menu')

        # select adjustments menu
        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Adjustments Menu')

        # enter adjustments menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_menu_selected", label='Standard Adjustments')

        # enter standard adjustments menu
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()

        self.assertEventCalledWith("service_settings_start", settings_label='Test1', value_label="B (default)")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_settings_start", settings_label='Test2', value_label="No (default)")

        # change setting
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_settings_edit", settings_label='Test2', value_label="No (default)")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_settings_edit", settings_label='Test2', value_label="Yes")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_settings_edit", settings_label='Test2', value_label="No (default)")

        self.hit_and_release_switch("s_service_down")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_settings_edit", settings_label='Test2', value_label="Yes")

        # exit setting change
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_settings_start", settings_label='Test1', value_label="B (default)")

        self.hit_and_release_switch("s_service_down")
        self.advance_time_and_run()
        self.assertEventCalledWith("service_settings_start", settings_label='Test2', value_label="Yes")

        self.assertEventNotCalled("service_settings_stop")

        # exit settings change
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()

        self.assertEventCalled("service_settings_stop")
