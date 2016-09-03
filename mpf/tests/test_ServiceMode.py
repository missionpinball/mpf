from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestServiceMode(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/service_mode/'

    def test_start_stop_service_in_attract(self):
        self.mock_event("service_door_opened")
        self.mock_event("service_door_closed")
        self.mock_event("service_mode_entered")
        self.mock_event("service_mode_exited")

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
        self.assertEventCalled('service_mode_exited', 2)
        self.assertEventCalled('service_door_closed', 1)
        self.assertModeRunning("attract")
        self.assertModeRunning("service")

    def test_start_stop_service_in_game(self):
        self.assertModeRunning("service")
        self.mock_event("service_door_opened")
        self.mock_event("service_door_closed")
        self.mock_event("service_mode_entered")
        self.mock_event("service_mode_exited")

        self.start_game()
        self.assertModeRunning("game")
        self.assertModeRunning("service")
        self.assertFalse(self.machine.switch_controller.is_active("s_door_open"))

        # open door. game still running
        self.hit_switch_and_run("s_door_open", 0)
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
        self.assertModeRunning("attract")
        self.assertEventCalled('service_mode_exited')

    def test_start_enter_service(self):
        pass
