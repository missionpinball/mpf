
from MpfTestCase import MpfTestCase
from mock import MagicMock


class TestTutorialStep9(MpfTestCase):

    def getConfigFile(self):
        return 'step9.yaml'

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

        self.assertEqual(5, self.machine.ball_devices.bd_trough.balls)

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(2)

        self.assertEqual(1, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)