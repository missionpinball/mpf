from mpf.tests.MpfTestCase import MpfTestCase, test_config_directory


class TestCustomCode(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/custom_code/'

    def test_scoring(self):
        self.mock_event("test_response")
        self.post_event("test_event")
        self.machine_run()

        self.assertEqual(1, self._events['test_response'])

    @test_config_directory('tests/machine_files/scriptlet/')
    def test_legacy_scriptlet(self):
        self.mock_event("test_response")
        self.post_event("test_event")
        self.machine_run()

        self.assertEqual(1, self._events['test_response'])
