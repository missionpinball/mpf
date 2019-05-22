"""Test event player."""
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.MpfGameTestCase import MpfGameTestCase

# How many test iterations do we run to convince of randomness?
RANDOM_RUNS = 20


class TestRandomEventPlayer(MpfTestCase):

    def getConfigFile(self):
        return 'test_random_event_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/event_players/'

    def test_machine_tests(self):
        tester = TestRandomEventPlayerBase(self, "machine")
        tester.run_all_tests()


class TestRandomEventPlayerGame(MpfGameTestCase):

    def getConfigFile(self):
        return 'test_random_event_player.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/event_players/'

    def get_platform(self):
        return 'smart_virtual'

    def test_player_tests(self):
        self.fill_troughs()
        self.start_game()
        self.advance_time_and_run(4)
        self.machine.events.post("start_mode2")
        self.advance_time_and_run(4)
        self.assertTrue(self.machine.modes.mode2.active)
        self.assertTrue(self.machine.mode_controller.is_active('mode2'))

        tester = TestRandomEventPlayerBase(self, "player")
        tester.run_all_tests()


# Below are the common setup and test run methods shared by the machine and player test cases
class TestRandomEventPlayerBase():
    def __init__(self, runner, scope, events=["event1", "event2", "event3", "event4"]):
        self.runner = runner
        self.scope = scope
        self.events = events
        for event in events:
            runner.machine.events.add_handler(event=event, handler=self._handle_event, event_name=event)

    def run_all_tests(self):
        for test in [self._test_force_different, self._test_force_all, self._test_disable_random]:
            test()

    def _reset(self):
        self.eventHistory = []
        self.uniqueEvents = set()
        self.prevEvent = None
        self.lastEvent = None

    def _handle_event(self, **kwargs):
        self.prevEvent = self.lastEvent
        self.lastEvent = kwargs['event_name']
        self.eventHistory.append(self.lastEvent)
        self.uniqueEvents.add(self.lastEvent)

    def _test_force_different(self):
        self._reset()
        for x in range(0, RANDOM_RUNS):
            self.runner.post_event("test_{}_force_different".format(self.scope))
            self.runner.advance_time_and_run()
            self.runner.assertNotEqual(self.prevEvent, self.lastEvent)

    def _test_force_all(self):
        self._reset()
        for x in range(0, RANDOM_RUNS):
            # If we have done all the events, reset the unique list
            if len(self.events) == len(self.uniqueEvents):
                self.uniqueEvents = set()
                self.eventHistory = []
            self.runner.post_event("test_{}_force_all".format(self.scope))
            self.runner.advance_time_and_run()
            self.runner.assertNotEqual(self.prevEvent, self.lastEvent)
            # If we force all, the set should always get an entry
            self.runner.assertEqual(len(self.uniqueEvents), len(self.eventHistory))

    def _test_disable_random(self):
        self._reset()
        # Set initial values for our lookback
        self.prevEvent = self.events[:1]
        for x in range(0, RANDOM_RUNS):
            expectedIdx = x % 4
            self.runner.post_event("test_{}_disable_random".format(self.scope))
            self.runner.advance_time_and_run()
            self.runner.assertNotEqual(self.prevEvent, self.lastEvent)
            self.runner.assertEqual(self.lastEvent, self.events[expectedIdx])
