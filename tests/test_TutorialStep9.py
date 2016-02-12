
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock


class TestTutorialStep9(MpfTestCase):

    def getConfigFile(self):
        return 'step9.yaml'

    def getMachinePath(self):
        return 'examples/tutorial/'

    def get_platform(self):
        return 'smart_virtual'

    def test_eject_to_pf(self):
        # start active switches should start with 5 balls in the trough
        self.assertEqual(5, self.machine.ball_devices.bd_trough.balls)

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(2)

        self.assertEqual(1, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)

        # player hits the launch button
        self.machine.switch_controller.process_switch('s_launch', 1)
        self.machine.switch_controller.process_switch('s_launch', 0)
        self.advance_time_and_run(4)

        self.assertEqual(0, self.machine.ball_devices.bd_plunger.balls)
        self.assertEqual(4, self.machine.ball_devices.bd_trough.balls)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)
