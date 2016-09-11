from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestDropTargets(MpfTestCase):

    def getConfigFile(self):
        return 'test_drop_targets.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/drop_targets/'

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
        self.machine.coils.coil1.pulse.assert_called_once_with()

        # after another 100ms the switches releases
        self.release_switch_and_run("switch1", 0)
        self.release_switch_and_run("switch2", 0)
        self.release_switch_and_run("switch3", 1)

        self.assertFalse(self.machine.drop_targets.left1.complete)
        self.assertFalse(self.machine.drop_targets.left2.complete)
        self.assertFalse(self.machine.drop_targets.left3.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank.complete)

    def test_knockdown_and_reset(self):
        self.machine.coils.coil2.pulse = MagicMock()
        self.machine.coils.coil3.pulse = MagicMock()

        self.assertFalse(self.machine.drop_targets.left6.complete)

        # knock it down
        self.post_event("knock_knock")
        self.advance_time_and_run(.3)
        assert not self.machine.coils.coil2.pulse.called
        self.machine.coils.coil3.pulse.assert_called_once_with()
        self.machine.coils.coil3.pulse = MagicMock()

        self.hit_switch_and_run("switch6", 1)
        self.assertTrue(self.machine.drop_targets.left6.complete)

        # reset again
        self.post_event("reset_target")
        self.advance_time_and_run(.3)
        self.machine.coils.coil2.pulse.assert_called_once_with()
        assert not self.machine.coils.coil3.pulse.called

        self.release_switch_and_run("switch6", 1)
        self.assertFalse(self.machine.drop_targets.left6.complete)

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
        self.release_switch_and_run("switch6", .1)

        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        # mode is running again. should complete
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

        self.machine.coils.coil2.pulse.assert_called_once_with()
        self.machine.coils.coil2.pulse.reset_mock()
        assert not self.machine.coils.coil3.pulse.called
        self.release_switch_and_run("switch6", 1)

        # knock down should work
        target.knockdown()
        self.advance_time_and_run()

        self.machine.coils.coil3.pulse.assert_called_once_with()
        self.machine.coils.coil3.pulse.reset_mock()
        assert not self.machine.coils.coil2.pulse.called
        self.hit_switch_and_run("switch6", 1)

        # but not when its down already
        target.knockdown()
        self.advance_time_and_run()
        assert not self.machine.coils.coil2.pulse.called
        assert not self.machine.coils.coil3.pulse.called
