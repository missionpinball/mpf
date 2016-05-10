from mpf.tests.MpfTestCase import MpfTestCase


class TestScriptlets(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/scriptlets/'

    def test_scoring(self):
        self.mock_event("test_response")
        self.post_event("test_event")
        self.machine_run()

        self.assertEqual(1, self._events['test_response'])
