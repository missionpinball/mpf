from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestComboSwitches(MpfTestCase):

    def getConfigFile(self):
        return 'combo_switches.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/combo_switches/'

    def test_tag_combo(self):
        self.mock_event('tag_combo_both')
        self.mock_event('tag_combo_inactive')
        self.mock_event('tag_combo_one')

        self.hit_switch_and_run('switch5', 1)
        self.assertEventNotCalled('tag_combo_both')
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventNotCalled('tag_combo_one')
        self.assertEqual(self.machine.combo_switches.tag_combo.state, 'inactive')

        self.hit_switch_and_run('switch7', 1)
        self.assertEventCalled('tag_combo_both')
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventNotCalled('tag_combo_one')
        self.assertEqual(self.machine.combo_switches.tag_combo.state, 'both')

        self.release_switch_and_run('switch7', 1)
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventCalled('tag_combo_one')
        self.assertEqual(self.machine.combo_switches.tag_combo.state, 'one')

        self.mock_event('tag_combo_both')
        self.mock_event('tag_combo_inactive')
        self.mock_event('tag_combo_one')

        self.hit_switch_and_run('switch7', 1)
        self.assertEventCalled('tag_combo_both')
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventNotCalled('tag_combo_one')

        self.release_switch_and_run('switch5', 1)
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventCalled('tag_combo_one')

        self.release_switch_and_run('switch7', 1)
        self.assertEventCalled('tag_combo_inactive')

        # now make sure it all works with the switches in the other order
        self.mock_event('tag_combo_both')
        self.mock_event('tag_combo_inactive')
        self.mock_event('tag_combo_one')

        self.hit_switch_and_run('switch7', 1)
        self.assertEventNotCalled('tag_combo_both')
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventNotCalled('tag_combo_one')

        self.hit_switch_and_run('switch5', 1)
        self.assertEventCalled('tag_combo_both')
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventNotCalled('tag_combo_one')

        self.release_switch_and_run('switch5', 1)
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventCalled('tag_combo_one')

        self.mock_event('tag_combo_both')
        self.mock_event('tag_combo_inactive')
        self.mock_event('tag_combo_one')

        self.hit_switch_and_run('switch5', 1)
        self.assertEventCalled('tag_combo_both')
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventNotCalled('tag_combo_one')

        self.release_switch_and_run('switch7', 1)
        self.assertEventNotCalled('tag_combo_inactive')
        self.assertEventCalled('tag_combo_one')

        self.release_switch_and_run('switch5', 1)
        self.assertEventCalled('tag_combo_inactive')

    def test_switch_combo(self):
        self.mock_event('switch_combo_both')
        self.mock_event('switch_combo_inactive')
        self.mock_event('switch_combo_one')

        self.hit_switch_and_run('switch1', 1)
        self.assertEventNotCalled('switch_combo_both')
        self.assertEventNotCalled('switch_combo_inactive')
        self.assertEventNotCalled('switch_combo_one')

        self.hit_switch_and_run('switch2', 1)
        self.assertEventCalled('switch_combo_both')
        self.assertEventNotCalled('switch_combo_inactive')
        self.assertEventNotCalled('switch_combo_one')

        self.release_switch_and_run('switch2', 1)
        self.assertEventNotCalled('switch_combo_inactive')
        self.assertEventCalled('switch_combo_one')

        self.mock_event('switch_combo_both')
        self.mock_event('switch_combo_inactive')
        self.mock_event('switch_combo_one')

        self.hit_switch_and_run('switch2', 1)
        self.assertEventCalled('switch_combo_both')
        self.assertEventNotCalled('switch_combo_inactive')
        self.assertEventNotCalled('switch_combo_one')

        self.release_switch_and_run('switch1', 1)
        self.assertEventNotCalled('switch_combo_inactive')
        self.assertEventCalled('switch_combo_one')

        self.release_switch_and_run('switch2', 1)
        self.assertEventCalled('switch_combo_inactive')

        # test long offset time
        self.mock_event('switch_combo_both')
        self.mock_event('switch_combo_inactive')
        self.mock_event('switch_combo_one')

        self.hit_switch_and_run('switch1', 100)
        self.assertEventNotCalled('switch_combo_both')

        self.hit_switch_and_run('switch2', .1)
        self.assertEventCalled('switch_combo_both')

    def test_multiple_switch_combo(self):

        # first test the basics with multiple switches listed

        self.mock_event('multiple_switch_combo_both')
        self.mock_event('multiple_switch_combo_inactive')
        self.mock_event('multiple_switch_combo_one')

        self.hit_switch_and_run('switch1', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        self.hit_switch_and_run('switch3', 1)
        self.assertEventCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        self.release_switch_and_run('switch3', 1)
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventCalled('multiple_switch_combo_one')

        self.mock_event('multiple_switch_combo_both')
        self.mock_event('multiple_switch_combo_inactive')
        self.mock_event('multiple_switch_combo_one')

        self.hit_switch_and_run('switch3', 1)
        self.assertEventCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        self.release_switch_and_run('switch1', 1)
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventCalled('multiple_switch_combo_one')

        self.release_switch_and_run('switch3', 1)
        self.assertEventCalled('multiple_switch_combo_inactive')

        # now start playing with combinations of switches from the same group

        self.mock_event('multiple_switch_combo_both')
        self.mock_event('multiple_switch_combo_inactive')
        self.mock_event('multiple_switch_combo_one')

        # hit switch 1, nothing happens
        self.hit_switch_and_run('switch1', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        # hit switch 2, which is in group 1, so still nothing happens
        self.hit_switch_and_run('switch2', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        # hit switch 3, which is in group 2, so we're active
        self.hit_switch_and_run('switch3', 1)
        self.assertEventCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        self.mock_event('multiple_switch_combo_both')
        self.mock_event('multiple_switch_combo_inactive')
        self.mock_event('multiple_switch_combo_one')

        # hit switch 4, in group 2, so nothing happens
        self.hit_switch_and_run('switch4', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        # release switch 3, but switch 4 is still active, so nothing happens
        self.release_switch_and_run('switch3', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        # release switch 2, but switch 1 is still active, so nothing happens
        self.release_switch_and_run('switch2', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventNotCalled('multiple_switch_combo_one')

        # release switch 1, the last from group 1, so now we have the one event
        self.release_switch_and_run('switch1', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventCalled('multiple_switch_combo_one')

        # hit switch 2, so now we go back to combo active
        self.hit_switch_and_run('switch2', 1)
        self.assertEventCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventCalled('multiple_switch_combo_one')

        self.mock_event('multiple_switch_combo_both')
        self.mock_event('multiple_switch_combo_inactive')
        self.mock_event('multiple_switch_combo_one')

        # release switch 4, so we go back to one is active
        self.release_switch_and_run('switch4', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventNotCalled('multiple_switch_combo_inactive')
        self.assertEventCalled('multiple_switch_combo_one')

        # release switch 2, so back to none are active
        self.release_switch_and_run('switch2', 1)
        self.assertEventNotCalled('multiple_switch_combo_both')
        self.assertEventCalled('multiple_switch_combo_inactive')
        self.assertEventCalled('multiple_switch_combo_one')

    def test_custom_offset(self):

        # we have a 1s offset

        self.mock_event('custom_offset_both')
        self.mock_event('custom_offset_inactive')
        self.mock_event('custom_offset_one')
        self.mock_event('custom_offset_switches_1')
        self.mock_event('custom_offset_switches_2')

        self.hit_switch_and_run('switch1', .1)
        self.assertEventNotCalled('custom_offset_switches_1')
        self.assertEventNotCalled('custom_offset_switches_2')
        self.advance_time_and_run(1.9)
        self.assertEventNotCalled('custom_offset_both')
        self.assertEventNotCalled('custom_offset_inactive')
        self.assertEventNotCalled('custom_offset_one')
        self.assertEventCalled('custom_offset_switches_1')
        self.assertEventNotCalled('custom_offset_switches_2')
        self.mock_event('custom_offset_switches_1')

        # switch2 in more than 1s offset time, so events should not be posted
        self.hit_switch_and_run('switch2', 1)
        self.assertEventNotCalled('custom_offset_both')
        self.assertEventNotCalled('custom_offset_inactive')
        self.assertEventNotCalled('custom_offset_one')
        self.assertEventNotCalled('custom_offset_switches_1')
        self.assertEventNotCalled('custom_offset_switches_2')

        self.release_switch_and_run('switch1', .1)
        self.release_switch_and_run('switch2', .1)

        # now hit both of the switches in < 1s
        self.hit_switch_and_run('switch1', .1)
        self.hit_switch_and_run('switch2', .1)
        self.assertEventCalled('custom_offset_both')
        self.advance_time_and_run(10)
        self.assertEventNotCalled('custom_offset_inactive')
        self.assertEventNotCalled('custom_offset_one')
        self.assertEventNotCalled('custom_offset_switches_1')
        self.assertEventNotCalled('custom_offset_switches_2')

    def test_custom_hold(self):

        # we have a 1s hold time

        self.mock_event('custom_hold_both')
        self.mock_event('custom_hold_inactive')
        self.mock_event('custom_hold_one')

        self.hit_switch_and_run('switch1', 5)
        self.hit_switch_and_run('switch2', .5)
        self.assertEventNotCalled('custom_hold_both')
        self.assertEventNotCalled('custom_hold_inactive')
        self.assertEventNotCalled('custom_hold_one')

        # advance more than 1s from the first switch, nothing should happen
        self.advance_time_and_run(.1)
        self.assertEventNotCalled('custom_hold_both')
        self.assertEventNotCalled('custom_hold_inactive')
        self.assertEventNotCalled('custom_hold_one')

        # advance more than 1s from the second switch
        self.advance_time_and_run(.6)
        self.assertEventCalled('custom_hold_both')
        self.assertEventNotCalled('custom_hold_inactive')
        self.assertEventNotCalled('custom_hold_one')

        # release one of the switches, one should be posted
        self.release_switch_and_run('switch2', .1)
        self.assertEventNotCalled('custom_hold_inactive')
        self.assertEventCalled('custom_hold_one')

        self.mock_event('custom_hold_both')
        self.mock_event('custom_hold_inactive')
        self.mock_event('custom_hold_one')

        # hit the second switch again, event should not be posted
        self.hit_switch_and_run('switch2', .5)
        self.assertEventNotCalled('custom_hold_both')
        self.assertEventNotCalled('custom_hold_inactive')
        self.assertEventNotCalled('custom_hold_one')

        # advance more than 1s to see the event
        self.advance_time_and_run(.6)
        self.assertEventCalled('custom_hold_both')
        self.assertEventNotCalled('custom_hold_inactive')
        self.assertEventNotCalled('custom_hold_one')

        # release both
        self.release_switch_and_run('switch1', .1)
        self.release_switch_and_run('switch2', .1)
        self.assertEventCalled('custom_hold_inactive')

    def test_custom_release(self):

        # release time of 1s

        self.mock_event('custom_release_both')
        self.mock_event('custom_release_inactive')
        self.mock_event('custom_release_one')

        # both switches should post both
        self.hit_switch_and_run('switch1', 1)
        self.hit_switch_and_run('switch2', .1)
        self.assertEventCalled('custom_release_both')
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # release 1, should not post one because it's less than 1s
        self.release_switch_and_run('switch2', .1)
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # wait more than 1s and one should be posted
        self.advance_time_and_run(1)
        self.assertEventCalled('custom_release_one')

        # release the other switch, inactive should not be posted yet
        self.release_switch_and_run('switch1', .1)
        self.assertEventNotCalled('custom_release_inactive')

        # wait more than 1s for the inactive event
        self.advance_time_and_run(1)
        self.assertEventCalled('custom_release_inactive')

        # start over
        self.hit_switch_and_run('switch1', 1)
        self.hit_switch_and_run('switch2', 1)

        self.mock_event('custom_release_both')
        self.mock_event('custom_release_inactive')
        self.mock_event('custom_release_one')

        # release and reactivate in less than 1s, no new events
        self.release_switch_and_run('switch2', .5)
        self.hit_switch_and_run('switch2', .1)

        self.assertEventNotCalled('custom_release_both')
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # make sure no new events after the initial release time passed
        self.advance_time_and_run(1)
        self.assertEventNotCalled('custom_release_both')
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # release and reactive both in less than 1s, no new events
        self.release_switch_and_run('switch1', .1)
        self.release_switch_and_run('switch2', .1)
        self.hit_switch_and_run('switch1', .1)
        self.hit_switch_and_run('switch2', .1)

        self.assertEventNotCalled('custom_release_both')
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # make sure no new events
        self.advance_time_and_run(1)
        self.assertEventNotCalled('custom_release_both')
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # now do the whole thing again, with the switches flipped

        self.release_switch_and_run('switch2', 2)

        self.mock_event('custom_release_both')
        self.mock_event('custom_release_inactive')
        self.mock_event('custom_release_one')

        # both switches should post both
        self.hit_switch_and_run('switch2', 1)
        self.hit_switch_and_run('switch1', .1)
        self.assertEventCalled('custom_release_both')
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # release 1, should not post one because it's less than 1s
        self.release_switch_and_run('switch1', .1)
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

        # wait more than 1s and one should be posted
        self.advance_time_and_run(1)
        self.assertEventCalled('custom_release_one')

        # release the other switch, inactive should not be posted yet
        self.release_switch_and_run('switch2', .1)
        self.assertEventNotCalled('custom_release_inactive')

        # wait more than 1s for the inactive event
        self.advance_time_and_run(1)
        self.assertEventCalled('custom_release_inactive')

        # start over
        self.hit_switch_and_run('switch2', 1)
        self.hit_switch_and_run('switch1', .1)

        self.mock_event('custom_release_both')
        self.mock_event('custom_release_inactive')
        self.mock_event('custom_release_one')

        # release and reactivate in less than 1s, no new events
        self.release_switch_and_run('switch1', .5)
        self.hit_switch_and_run('switch1', .1)

        self.assertEventNotCalled('custom_release_both')
        self.assertEventNotCalled('custom_release_inactive')
        self.assertEventNotCalled('custom_release_one')

    def test_custom_times_multiple_switches(self):

        # this is a sort of catch all with all three types of custom times,
        # but with multiple switches

        # time is >1s from the first switch
        self._reset_custom_times_multiple_switches()
        self.hit_switch_and_run('switch5', .5)
        self.hit_switch_and_run('switch6', .6)
        self.hit_switch_and_run('switch7', .1)
        self.assertEventNotCalled('custom_times_multiple_switches_both')

        # time is <1s from first switch
        self._reset_custom_times_multiple_switches()
        self.hit_switch_and_run('switch5', .5)
        self.hit_switch_and_run('switch6', .1)
        self.hit_switch_and_run('switch7', .1)
        self.assertEventNotCalled('custom_times_multiple_switches_both')

        # there's a 1s hold time
        self.advance_time_and_run(1.1)
        self.assertEventCalled('custom_times_multiple_switches_both')

        # release switch7, one event should post after 1s
        self.release_switch_and_run('switch7', .1)
        self.assertEventNotCalled('custom_times_multiple_switches_one')
        self.advance_time_and_run(1)
        self.assertEventCalled('custom_times_multiple_switches_one')

        # test hold time
        self._reset_custom_times_multiple_switches()
        self.hit_switch_and_run('switch5', .1)
        self.hit_switch_and_run('switch6', .1)
        self.hit_switch_and_run('switch7', .1)
        self.assertEventNotCalled('custom_times_multiple_switches_both')
        self.advance_time_and_run(1)
        self.assertEventCalled('custom_times_multiple_switches_both')

    def _reset_custom_times_multiple_switches(self):
        self.release_switch_and_run('switch5', .1)
        self.release_switch_and_run('switch6', .1)
        self.release_switch_and_run('switch7', .1)
        self.release_switch_and_run('switch8', .1)
        self.advance_time_and_run(2)
        self.mock_event('custom_times_multiple_switches_both')
        self.mock_event('custom_times_multiple_switches_inactive')
        self.mock_event('custom_times_multiple_switches_one')

    def test_custom_events(self):
        self.mock_event('custom_events_both')
        self.mock_event('custom_events_inactive')
        self.mock_event('custom_events_one')
        self.mock_event('active_event')
        self.mock_event('active_event2')
        self.mock_event('inactive_event')
        self.mock_event('one_event')

        self.hit_switch_and_run('switch1', .1)
        self.hit_switch_and_run('switch2', .1)
        self.release_switch_and_run('switch1', .1)
        self.release_switch_and_run('switch2', .1)

        self.assertEventNotCalled('custom_events_both')
        self.assertEventNotCalled('custom_events_inactive')
        self.assertEventNotCalled('custom_events_one')
        self.assertEventCalled('active_event')
        self.assertEventCalled('active_event2')
        self.assertEventCalled('inactive_event')
        self.assertEventCalled('one_event')

    def test_combo_switches_in_mode(self):
        self.mock_event('mode1_combo_both')
        self.mock_event('mode1_combo_inactive')
        self.mock_event('mode1_combo_one')

        self.hit_switch_and_run('switch1', .1)
        self.hit_switch_and_run('switch2', .1)
        self.release_switch_and_run('switch1', .1)
        self.release_switch_and_run('switch2', .1)

        self.assertEventNotCalled('mode1_combo_both')
        self.assertEventNotCalled('mode1_combo_inactive')
        self.assertEventNotCalled('mode1_combo_one')

        self.advance_time_and_run(5)

        self.machine.modes.mode1.start()
        self.advance_time_and_run()

        self.hit_switch_and_run('switch1', .1)
        self.hit_switch_and_run('switch2', .1)
        self.release_switch_and_run('switch1', .1)
        self.release_switch_and_run('switch2', .1)

        self.assertEventCalled('mode1_combo_both')
        self.assertEventCalled('mode1_combo_inactive')
        self.assertEventCalled('mode1_combo_one')

        self.machine.modes.mode1.stop()
        self.advance_time_and_run()
        self.mock_event('mode1_combo_both')
        self.mock_event('mode1_combo_inactive')
        self.mock_event('mode1_combo_one')

        self.hit_switch_and_run('switch1', .1)
        self.hit_switch_and_run('switch2', .1)
        self.release_switch_and_run('switch1', .1)
        self.release_switch_and_run('switch2', .1)

        self.assertEventNotCalled('mode1_combo_both')
        self.assertEventNotCalled('mode1_combo_inactive')
        self.assertEventNotCalled('mode1_combo_one')

    def test_built_in_combos(self):
        self.mock_event('flipper_cancel')
        self.hit_switch_and_run('switch9', .1)
        self.hit_switch_and_run('switch10', .1)
        self.assertEventCalled('flipper_cancel')

        # make sure it works with long times too
        self.release_switch_and_run('switch9', .1)
        self.release_switch_and_run('switch10', .1)

        self.mock_event('flipper_cancel')
        self.hit_switch_and_run('switch9', 10)
        self.hit_switch_and_run('switch10', .1)
        self.assertEventCalled('flipper_cancel')
