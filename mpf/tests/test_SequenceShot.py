"""Test sequence shots."""
from mpf.tests.MpfTestCase import MpfTestCase


class TestShots(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/sequence_shot/'

    def test_simple_sequence(self):
        self.mock_event("sequence1_complete")
        self.post_event("event1")
        self.machine_run()
        self.post_event("event2")
        self.machine_run()
        self.assertEventNotCalled("sequence1_complete")
        self.post_event("event3")
        self.machine_run()
        self.assertEventCalled("sequence1_complete")
        self.mock_event("sequence1_complete")
        self.post_event("event1")
        self.machine_run()
        self.post_event("event2")
        self.machine_run()
        self.assertEventNotCalled("sequence1_complete")
        self.post_event("event3")
        self.machine_run()
        self.assertEventCalled("sequence1_complete")

    def test_delay(self):
        self.mock_event("sequence1_complete")
        self.post_event("delay1")
        # no success after delay
        self.machine_run()
        self.post_event("event1")
        self.machine_run()
        self.post_event("event2")
        self.machine_run()
        self.post_event("event3")
        self.machine_run()
        self.assertEventNotCalled("sequence1_complete")

        # works after delay
        self.advance_time_and_run(1.5)
        self.post_event("event1")
        self.machine_run()
        self.post_event("event2")
        self.machine_run()
        self.assertEventNotCalled("sequence1_complete")
        self.post_event("event3")
        self.machine_run()
        self.assertEventCalled("sequence1_complete")

    def test_delay_switch(self):
        self.mock_event("sequence2_complete")
        self.hit_and_release_switch("seq2_delay")
        self.machine_run()
        self.hit_and_release_switch("seq2_1")
        self.machine_run()
        self.hit_and_release_switch("seq2_2")
        self.machine_run()
        self.hit_and_release_switch("seq2_3")
        self.machine_run()
        self.assertEventNotCalled("sequence2_complete")

        # works after delay
        self.advance_time_and_run(1.5)
        self.hit_and_release_switch("seq2_1")
        self.machine_run()
        self.hit_and_release_switch("seq2_2")
        self.machine_run()
        self.assertEventNotCalled("sequence2_complete")
        self.hit_and_release_switch("seq2_3")
        self.machine_run()
        self.assertEventCalled("sequence2_complete")

    def test_simple_switch_sequence(self):
        self.mock_event("sequence2_complete")
        self.hit_and_release_switch("seq2_1")
        self.machine_run()
        self.hit_and_release_switch("seq2_2")
        self.machine_run()
        self.assertEventNotCalled("sequence2_complete")
        self.hit_and_release_switch("seq2_3")
        self.machine_run()
        self.assertEventCalled("sequence2_complete")

    def test_cancel(self):
        self.mock_event("sequence1_complete")
        self.post_event("event1")
        self.machine_run()
        self.post_event("event2")
        self.machine_run()
        self.assertEventNotCalled("sequence1_complete")
        self.post_event("cancel")
        self.machine_run()
        self.post_event("event3")
        self.machine_run()
        self.assertEventNotCalled("sequence1_complete")

    def test_cancel_switch(self):
        self.mock_event("sequence2_complete")
        self.hit_and_release_switch("seq2_1")
        self.machine_run()
        self.hit_and_release_switch("seq2_2")
        self.machine_run()
        self.assertEventNotCalled("sequence2_complete")
        self.hit_and_release_switch("seq2_cancel")
        self.hit_and_release_switch("seq2_3")
        self.machine_run()
        self.assertEventNotCalled("sequence2_complete")

    def test_single_step_sequence(self):
        self.mock_event("sequence3_complete")
        self.post_event("event3_1")
        self.machine_run()
        self.assertEventCalled("sequence3_complete")

    def test_interleaved_sequences(self):
        """"Two balls pass through the sequence."""
        self.mock_event("sequence1_complete")

        self.post_event("event1")
        self.advance_time_and_run(.2)
        self.post_event("event1")
        self.advance_time_and_run(.1)

        self.post_event("event2")
        self.advance_time_and_run(.2)
        self.post_event("event2")
        self.advance_time_and_run(.1)

        self.assertEventNotCalled("sequence1_complete")
        self.post_event("event3")
        self.advance_time_and_run(.2)
        self.assertEventCalled("sequence1_complete")
        self.mock_event("sequence1_complete")
        self.post_event("event3")
        self.assertEventCalled("sequence1_complete")

    def test_sequence_timeout(self):
        """Ball rolls up a ramp and back down."""
        self.mock_event("sequence1_complete")
        self.mock_event("sequence1_timeout")
        self.post_event("event1")
        self.advance_time_and_run(.2)
        self.post_event("event2")
        self.advance_time_and_run(.1)
        self.post_event("event2")
        self.advance_time_and_run(.2)
        self.post_event("event1")
        self.advance_time_and_run(.1)
        self.assertEventNotCalled("sequence1_complete")
        self.assertEventNotCalled("sequence1_timeout")
        self.advance_time_and_run(2.5)
        self.assertEventCalled("sequence1_timeout", times=1)
        self.advance_time_and_run(.5)
        # second timeout from interleaved sequence. can we prevent this?
        self.assertEventCalled("sequence1_timeout", times=2)
