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

        # after another 100ms the switches relesae
        self.release_switch_and_run("switch1", 0)
        self.release_switch_and_run("switch2", 0)
        self.release_switch_and_run("switch3", 1)

        self.assertFalse(self.machine.drop_targets.left1.complete)
        self.assertFalse(self.machine.drop_targets.left2.complete)
        self.assertFalse(self.machine.drop_targets.left3.complete)
        self.assertFalse(self.machine.drop_target_banks.left_bank.complete)

    def test_drop_targets_in_mode(self):
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        self.assertIn('left4', self.machine.drop_targets)
        self.assertIn('left5', self.machine.drop_targets)
        self.assertIn('left6', self.machine.drop_targets)
        self.assertIn('left_bank_2', self.machine.drop_target_banks)

        self.machine.modes['mode1'].stop()
