
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestTutorialStep8(MpfTestCase):

    def getConfigFile(self):
        return 'step8.yaml'

    def getMachinePath(self):
        return '../examples/tutorial/'

    def get_platform(self):
        return 'smart_virtual'

    def test_flippers(self):
        # really this is just testing the everything loads without errors since
        # there's not much going on yet.
        self.assertIn('left_flipper', self.machine.flippers)
        self.assertIn('right_flipper', self.machine.flippers)

    def test_ball_devices(self):
        # start active switches should start with 5 balls in the trough
        self.assertEqual(5, self.machine.ball_devices.bd_trough.balls)

    def test_trough_eject(self):
        self.machine.ball_devices.bd_trough.eject()
        self.advance_time_and_run(11)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)
