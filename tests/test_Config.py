from MpfTestCase import MpfTestCase

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
        self.assertEquals('on', self.machine.config['test_section']['on_string'])
        self.assertEquals('off', self.machine.config['test_section']['off_string'])
        self.assertEquals(6400, self.machine.config['test_section']['int_6400'])
        self.assertEquals(3200, self.machine.config['test_section']['int_3200'])
        self.assertEquals(6, self.machine.config['test_section']['int_6'])
        self.assertEquals(7, self.machine.config['test_section']['int_7'])
        self.assertEquals(6400, self.machine.config['test_section']['int_6400'])
        self.assertEquals('00ff00', self.machine.config['test_section']['str_00ff00'])