
from MpfTestCase import MpfTestCase
from mock import MagicMock


class TestTutorialStep8(MpfTestCase):

    def getConfigFile(self):
        return 'step8.yaml'

    def getMachinePath(self):
        return '../machine_files/tutorial/'

    def get_platform(self):
        return 'smart_virtual'

    def test_flippers(self):
        # really this is just testing the everything loads without errors since
        # there's not much going on yet.
        self.assertIn('left_flipper', self.machine.flippers)
        self.assertIn('right_flipper', self.machine.flippers)

    def test_ball_devices(self):
        self.assertEqual(self.machine.ball_devices.bd_trough.balls,
                         5)
