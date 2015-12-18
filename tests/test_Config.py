from .MpfTestCase import MpfTestCase

class TestConfig(MpfTestCase):

    def getConfigFile(self):
        return 'test_config_interface.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/config_interface/'

    def test_config_file(self):
        self.assertIs(True, self.machine.config['test_section']['true_key1'])
        self.assertIs(True, self.machine.config['test_section']['true_key2'])
        self.assertIs(True, self.machine.config['test_section']['true_key3'])
        self.assertIs(True, self.machine.config['test_section']['true_key4'])
        self.assertIs(False, self.machine.config['test_section']['false_key1'])
        self.assertIs(False, self.machine.config['test_section']['false_key2'])
        self.assertIs(False, self.machine.config['test_section']['false_key3'])
        self.assertIs(False, self.machine.config['test_section']['false_key4'])
        self.assertEqual('on', self.machine.config['test_section']['on_string'])
        self.assertEqual('off', self.machine.config['test_section']['off_string'])
        self.assertEqual(6400, self.machine.config['test_section']['int_6400'])
        self.assertEqual(3200, self.machine.config['test_section']['int_3200'])
        self.assertEqual(6, self.machine.config['test_section']['int_6'])
        self.assertEqual(7, self.machine.config['test_section']['int_7'])
        self.assertEqual(6400, self.machine.config['test_section']['int_6400'])
        self.assertEqual('00ff00', self.machine.config['test_section']['str_00ff00'])