from mpf.tests.MpfTestCase import MpfTestCase


class TestDropTargets(MpfTestCase):

    def getConfigFile(self):
        return 'test_drop_targets.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/drop_targets/'

    def test_drop_targets(self):
        self.assertIn('left1', self.machine.drop_targets)
        self.assertIn('left2', self.machine.drop_targets)
        self.assertIn('left3', self.machine.drop_targets)
        self.assertIn('left_bank', self.machine.drop_target_banks)

    def test_drop_targets_in_mode(self):
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        self.assertIn('left4', self.machine.drop_targets)
        self.assertIn('left5', self.machine.drop_targets)
        self.assertIn('left6', self.machine.drop_targets)
        self.assertIn('left_bank_2', self.machine.drop_target_banks)

        self.machine.modes['mode1'].stop()
