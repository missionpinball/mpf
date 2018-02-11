from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestStateMachine(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/state_machine/'

    def test_state_machine(self):
        self.assertEqual("start", self.machine.state_machines.my_state.state)

        self.mock_event("step1_start")
        self.mock_event("step1_stop")
        self.mock_event("going_to_step2")
        self.post_event("state_machine_proceed")
        self.assertEqual("step1", self.machine.state_machines.my_state.state)
        self.assertEqual("on", self.machine.state_machines.my_state._show.name)
        self.assertEventCalled("step1_start")
        self.mock_event("step1_start")
        self.assertEventNotCalled("step1_stop")
        self.assertEventNotCalled("going_to_step2")
        self.post_event("state_machine_proceed")
        self.assertEqual("step1", self.machine.state_machines.my_state.state)
        self.assertEventNotCalled("step1_start")
        self.assertEventNotCalled("step1_stop")
        self.assertEventNotCalled("going_to_step2")

        self.post_event("state_machine_proceed2")
        self.assertEqual("step2", self.machine.state_machines.my_state.state)
        self.assertEqual(None, self.machine.state_machines.my_state._show)
        self.assertEventNotCalled("step1_start")
        self.assertEventCalled("step1_stop")
        self.assertEventCalled("going_to_step2")
        self.post_event("state_machine_proceed2")
        self.assertEqual("step2", self.machine.state_machines.my_state.state)

        self.post_event("state_machine_proceed3")
        self.assertEqual("start", self.machine.state_machines.my_state.state)

        self.post_event("state_machine_proceed")
        self.assertEqual("step1", self.machine.state_machines.my_state.state)

        self.post_event("state_machine_reset")
        self.assertEqual("start", self.machine.state_machines.my_state.state)
