from tests.MpfTestCase import MpfTestCase

class TestConfig(MpfTestCase):

    def getConfigFile(self):
        return 'test_config_interface.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/config_interface/'

    def test_config_file(self):
        # true, True, yes, Yes values should be True
        self.assertIs(True, self.machine.config['test_section']['true_key1'])
        self.assertIs(True, self.machine.config['test_section']['true_key2'])
        self.assertIs(True, self.machine.config['test_section']['true_key3'])
        self.assertIs(True, self.machine.config['test_section']['true_key4'])

        # false, False, no, No values should be False
        self.assertIs(False, self.machine.config['test_section']['false_key1'])
        self.assertIs(False, self.machine.config['test_section']['false_key2'])
        self.assertIs(False, self.machine.config['test_section']['false_key3'])
        self.assertIs(False, self.machine.config['test_section']['false_key4'])

        # on, off values should be strings
        self.assertEqual('on', self.machine.config['test_section']['on_string'])
        self.assertEqual('off', self.machine.config['test_section']['off_string'])

        # 6400, 003200, 6, 07 should be ints
        self.assertEqual(6400, self.machine.config['test_section']['int_6400'])
        self.assertEqual(3200, self.machine.config['test_section']['int_3200'])
        self.assertEqual(6, self.machine.config['test_section']['int_6'])
        self.assertEqual(7, self.machine.config['test_section']['int_7'])

        # 00ff00 should be string
        self.assertEqual('00ff00', self.machine.config['test_section']['str_00ff00'])

        # keys should be all lowercase
        self.assertIn('case_sensitive_1', self.machine.config['test_section'])
        self.assertIn('case_sensitive_2', self.machine.config['test_section'])
        self.assertIn('case_sensitive_3', self.machine.config['test_section'])

        # values should be case sensitive
        self.assertEqual(self.machine.config['test_section']['case_sensitive_1'], 'test')
        self.assertEqual(self.machine.config['test_section']['case_sensitive_2'], 'test')
        self.assertEqual(self.machine.config['test_section']['case_sensitive_3'], 'Test')

