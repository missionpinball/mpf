from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestDropTargets(MpfTestCase):

    def getConfigFile(self):
        return 'test_drop_targets.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/drop_targets/'

    def get_platform(self):
        return 'smart_virtual'

    def test_drop_target_bank(self):
        self.assertIn('left1', self.machine.drop_targets)
        self.assertIn('left2', self.machine.drop_targets)
        self.assertIn('left3', self.machine.drop_targets)
        self.assertIn('left_bank', self.machine.drop_target_banks)

        self.machine.coils.coil1.pulse = MagicMock()

        self.assertFalse(self.machine.drop_targets.left1.complete)
        self.assertFalse(self.machine.drop_targets.left2.complete)
        self.assertFalse(self.machine.drop_targets.left3.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank.complete)

        self.hit_switch_and_run("switch1", 1)
        self.hit_switch_and_run("switch2", 1)
        self.assertTrue(self.machine.drop_targets.left1.complete)
        self.assertTrue(self.machine.drop_targets.left2.complete)
        self.assertFalse(self.machine.drop_targets.left3.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank.complete)

        assert not self.machine.coils.coil1.pulse.called

        self.hit_switch_and_run("switch3", .5)
        self.assertTrue(self.machine.drop_targets.left1.complete)
        self.assertTrue(self.machine.drop_targets.left2.complete)
        self.assertTrue(self.machine.drop_targets.left3.complete)
        self.assertTrue(self.machine.drop_target_banks.left_bank.complete)

        assert not self.machine.coils.coil1.pulse.called

        # it should reset after 1s
        self.advance_time_and_run(.5)
        self.machine.coils.coil1.pulse.assert_called_once_with(max_wait_ms=100)

        # after another 100ms the switches releases
        self.release_switch_and_run("switch1", 0)
        self.release_switch_and_run("switch2", 0)
        self.release_switch_and_run("switch3", 1)

        self.assertFalse(self.machine.drop_targets.left1.complete)
        self.assertFalse(self.machine.drop_targets.left2.complete)
        self.assertFalse(self.machine.drop_targets.left3.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank.complete)

    def test_knockdown_and_reset(self):
        self.mock_event("unexpected_ball_on_playfield")
        self.machine.coils.coil2.pulse = MagicMock(wraps=self.machine.coils.coil2.pulse)
        self.machine.coils.coil3.pulse = MagicMock(wraps=self.machine.coils.coil3.pulse)

        self.assertFalse(self.machine.drop_targets.left6.complete)

        # knock it down
        self.post_event("knock_knock")
        self.advance_time_and_run(.3)
        assert not self.machine.coils.coil2.pulse.called
        self.machine.coils.coil3.pulse.assert_called_once_with(max_wait_ms=100)

        # ignore ms means the state is not updated yet
        self.assertFalse(self.machine.drop_targets.left6.complete)
        self.advance_time_and_run(.3)

        # and now it is
        self.assertTrue(self.machine.drop_targets.left6.complete)

        # reset it
        self.machine.coils.coil3.pulse.reset_mock()

        self.post_event("reset_target")
        self.advance_time_and_run(.3)
        assert not self.machine.coils.coil3.pulse.called
        self.machine.coils.coil2.pulse.assert_called_once_with(max_wait_ms=100)

        # ignore ms means the state is not updated yet
        self.assertTrue(self.machine.drop_targets.left6.complete)
        self.advance_time_and_run(6)

        # and now it is
        self.assertFalse(self.machine.drop_targets.left6.complete)

        self.assertEventNotCalled("unexpected_ball_on_playfield")

    def test_drop_targets_in_mode(self):
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        self.machine.coils.coil2.pulse = MagicMock()

        self.assertFalse(self.machine.drop_targets.left4.complete)
        self.assertFalse(self.machine.drop_targets.left5.complete)
        self.assertFalse(self.machine.drop_targets.left6.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank_2.complete)

        self.hit_switch_and_run("switch4", 1)
        self.hit_switch_and_run("switch5", 1)
        self.assertTrue(self.machine.drop_targets.left4.complete)
        self.assertTrue(self.machine.drop_targets.left5.complete)
        self.assertFalse(self.machine.drop_targets.left6.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank_2.complete)

        self.machine.modes['mode1'].stop()
        self.advance_time_and_run()

        self.assertTrue(self.machine.drop_targets.left4.complete)
        self.assertTrue(self.machine.drop_targets.left5.complete)
        self.assertFalse(self.machine.drop_targets.left6.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank_2.complete)

        # should not complete the bank
        self.hit_switch_and_run("switch6", .1)

        self.assertTrue(self.machine.drop_targets.left4.complete)
        self.assertTrue(self.machine.drop_targets.left5.complete)
        self.assertTrue(self.machine.drop_targets.left6.complete)

        self.assertFalse(self.machine.drop_target_banks.left_bank_2.complete)

        self.post_event("reset_target")

        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        # mode is running again. should complete
        self.hit_switch_and_run("switch4", .1)
        self.hit_switch_and_run("switch5", .1)
        self.hit_switch_and_run("switch6", .1)

        self.assertTrue(self.machine.drop_targets.left4.complete)
        self.assertTrue(self.machine.drop_targets.left5.complete)
        self.assertTrue(self.machine.drop_targets.left6.complete)

        self.assertTrue(self.machine.drop_target_banks.left_bank_2.complete)

    def test_drop_target_reset(self):
        target = self.machine.drop_targets.left6
        self.machine.coils.coil2.pulse = MagicMock()
        self.machine.coils.coil3.pulse = MagicMock()
        self.assertFalse(self.machine.switch_controller.is_active("switch6"))

        # target up. it should not reset
        target.reset()
        self.advance_time_and_run()

        assert not self.machine.coils.coil2.pulse.called
        assert not self.machine.coils.coil3.pulse.called

        # hit target down
        self.hit_switch_and_run("switch6", 1)
        self.assertTrue(target.complete)

        # it should reset
        target.reset()
        self.advance_time_and_run()

        self.machine.coils.coil2.pulse.assert_called_once_with(max_wait_ms=100)
        self.machine.coils.coil2.pulse.reset_mock()
        assert not self.machine.coils.coil3.pulse.called
        self.release_switch_and_run("switch6", 1)

        # knock down should work
        target.knockdown()
        self.advance_time_and_run()

        self.machine.coils.coil3.pulse.assert_called_once_with(max_wait_ms=100)
        self.machine.coils.coil3.pulse.reset_mock()
        assert not self.machine.coils.coil2.pulse.called
        self.hit_switch_and_run("switch6", 1)

        # but not when its down already
        target.knockdown()
        self.advance_time_and_run()
        assert not self.machine.coils.coil2.pulse.called
        assert not self.machine.coils.coil3.pulse.called

    def test_drop_target_ignore_ms(self):

        self.mock_event('drop_target_center1_down')
        self.mock_event('drop_target_center1_up')

        self.hit_switch_and_run('switch10', 1)
        self.assertSwitchState('switch10', True)  # ###############

        self.assertEventNotCalled('drop_target_center1_up')
        self.assertEventCalled('drop_target_center1_down')

        self.post_event('reset_center1', .05)
        self.release_switch_and_run('switch10', .1)
        self.hit_switch_and_run('switch10', .1)
        self.release_switch_and_run('switch10', .1)
        self.assertSwitchState('switch10', False)

        self.advance_time_and_run(.5)

        # reset happened in the ignore window so this event should not be
        # called
        self.assertEventNotCalled('drop_target_center1_up')
        self.advance_time_and_run(1)

        # now do the same test for knockdown

        self.mock_event('drop_target_center1_down')

        self.post_event('knockdown_center1', .2)
        self.hit_switch_and_run('switch10', .1)
        self.assertEventNotCalled('drop_target_center1_down')

        self.advance_time_and_run(1)
        self.assertEventCalled('drop_target_center1_down')

    def test_drop_target_bank_ignore_ms(self):
        self.mock_event('drop_target_bank_right_bank_down')
        self.mock_event('drop_target_bank_right_bank_mixed')

        self.hit_switch_and_run('switch8', 1)
        self.hit_switch_and_run('switch9', 1)

        self.assertEventCalled('drop_target_bank_right_bank_mixed', 1)
        self.assertEventCalled('drop_target_bank_right_bank_down', 1)

        self.mock_event('drop_target_bank_right_bank_down')
        self.mock_event('drop_target_bank_right_bank_mixed')
        self.mock_event('drop_target_bank_right_bank_up')

        self.post_event('reset_right_bank', .5)

        # these events should not be called since we're in the ignore window
        self.assertEventNotCalled('drop_target_bank_right_bank_mixed')
        self.assertEventNotCalled('drop_target_bank_right_bank_up')

        self.advance_time_and_run(1)

        # after 1s, the ignore is cleared and the bank updates its state.

        # mixed should not have been called since it happened during the
        # ignore window
        self.assertEventNotCalled('drop_target_bank_right_bank_mixed')

        # up should have been called by now
        self.assertEventCalled('drop_target_bank_right_bank_up')
