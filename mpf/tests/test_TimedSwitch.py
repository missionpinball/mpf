from mpf.tests.MpfTestCase import MpfTestCase


class TestTimedSwitch(MpfTestCase):

    def getConfigFile(self):
        return 'timed_switches.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/timed_switches/'

    def test_in_mode(self):
        self.start_mode("mode1")
        self.mock_event('mode_switch_active')
        self.mock_event('mode_switch_released')

        self.hit_switch_and_run("switch2", 1.1)
        self.assertEventNotCalled("mode_switch_active")
        self.advance_time_and_run()
        self.assertEventCalled("mode_switch_active")

    def test_timed_switches(self):

        # test single switch

        self.mock_event('group1_active')
        self.mock_event('group1_released')

        self.hit_switch_and_run('switch1', 1)
        self.assertEventNotCalled('group1_active')
        self.assertEventNotCalled('group1_released')

        self.advance_time_and_run(1.1)
        self.assertEventCalled('group1_active')
        self.assertEventNotCalled('group1_released')

        self.advance_time_and_run(10)
        self.assertEventCalled('group1_active', 1)
        self.assertEventNotCalled('group1_released')

        self.release_switch_and_run('switch1', .1)
        self.assertEventCalled('group1_released')

        # test 2 switches together
        self.mock_event('group1_active')
        self.mock_event('group1_released')

        self.hit_switch_and_run('switch1', 1)
        self.assertEventNotCalled('group1_active')
        self.assertEventNotCalled('group1_released')

        self.advance_time_and_run(1.1)
        self.assertEventCalled('group1_active')
        self.assertEventNotCalled('group1_released')

        self.hit_switch_and_run('switch2', 3)
        self.assertEventCalled('group1_active')
        self.assertEventNotCalled('group1_released')

        self.release_switch_and_run('switch1', .1)
        self.assertEventCalled('group1_active', 1)
        self.assertEventNotCalled('group1_released')

        self.release_switch_and_run('switch2', .1)
        self.assertEventCalled('group1_active', 1)
        self.assertEventCalled('group1_released')

        # test inverted state & custom events

        self.mock_event('active_event')
        self.mock_event('release_event')

        self.hit_switch_and_run('switch3', 5)
        self.assertEventNotCalled('active_event')
        self.assertEventNotCalled('release_event')

        self.release_switch_and_run('switch3', 1)
        self.assertEventNotCalled('active_event')
        self.assertEventNotCalled('release_event')

        self.advance_time_and_run(2)
        self.assertEventCalled('active_event')
        self.assertEventNotCalled('release_event')

        self.hit_switch_and_run('switch3', .1)
        self.assertEventCalled('active_event')
        self.assertEventCalled('release_event')

        # test built-in flipper cradle (also tests tags)

        self.mock_event('flipper_cradle')
        self.mock_event('flipper_cradle_release')

        self.hit_switch_and_run('switch4', 1)
        self.assertEventNotCalled('flipper_cradle')
        self.assertEventNotCalled('flipper_cradle_release')

        self.advance_time_and_run(3)
        self.assertEventCalled('flipper_cradle')
        self.assertEventNotCalled('flipper_cradle_release')

        # tap the second flipper
        self.hit_and_release_switch('switch5')
        self.assertEventNotCalled('flipper_cradle_release')

        # release the initial switch
        self.release_switch_and_run('switch4', 1)
        self.assertEventCalled('flipper_cradle_release')
