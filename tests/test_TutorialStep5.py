
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestTutorialStep5(MpfTestCase):

    def getConfigFile(self):
        return 'step5.yaml'

    def getMachinePath(self):
        return '../examples/tutorial/'

    def get_platform(self):
        return 'smart_virtual'

    def test_flippers(self):
        # really this is just testing the everything loads without errors since
        # there's not much going on yet.
        assert 'left_flipper' in self.machine.flippers
        assert 'right_flipper' in self.machine.flippers
