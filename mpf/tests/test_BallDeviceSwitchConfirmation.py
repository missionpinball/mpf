from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDeviceSwitchConfirmation(MpfTestCase):
    def __init__(self, test_map):
        super().__init__(test_map)
        self._captured = 0
        self._enter = -1
        self._missing = 0
        self._requesting = 0
        self._queue = False

    def getConfigFile(self):
        return 'test_ball_device_switch_confirmation.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def _missing_ball(self):
        self._missing += 1

    def _requesting_ball(self, balls, **kwargs):
        del kwargs
        self._requesting += balls

    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        del unclaimed_balls
        del kwargs
        self._enter += new_balls

    def _captured_from_pf(self, balls, **kwargs):
        del kwargs
        self._captured += balls

    def _hit_confirm(self):
        self.machine.switch_controller.process_switch("s_launcher_confirm", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_launcher_confirm", 0)
        self.advance_time_and_run(0.1)

    def test_eject_successful_to_other_trough(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter',
                                        self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = -1

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self._hit_confirm()
        self.advance_time_and_run(1)

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(0, self._enter)
        self.assertEqual(-1, self._captured)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, self._missing)

    def test_eject_no_confirm_but_target_enter(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter',
                                        self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = -1
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = 0

        # assume we have more than one ball to prevent BallController from "fixing" pf
        self.machine.ball_controller.num_balls_known = 5

        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)
        self.assertEqual(0, playfield.unexpected_balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)
        self.assertEqual(1, playfield.unexpected_balls)
        self.assertEqual(-1, playfield.available_balls)
        self.assertEqual(0, playfield.balls)

        # eject will fail since the eject_confirm switch was not hit
        self.advance_time_and_run(30)
        self.advance_time_and_run(30)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(0, self._enter)
        self.assertEqual(1, self._captured)

        # no ball on pf because the pf saw an unexpected ball
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)
        self.assertEqual(0, playfield.unexpected_balls)
        self.assertEqual(1, self._missing)

    def test_eject_successful_but_ball_never_arrives(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter',
                                        self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self._hit_confirm()
        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)

        # ball never arrives
        self.advance_time_and_run(300)

        # ball should be at playfield by now and got missing
        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, self._missing)

        # target2 captures and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(1, self._enter)
        self.assertEqual(1, self._captured)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._missing)

    def test_eject_successful_but_ball_never_arrives_and_drain(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(None, self.machine.game)

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)
        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual("idle", device1._state)
        self.assertEqual("ejecting", device2._state)
        self.assertEqual("waiting_for_ball", device3._state)
        self.assertEqual("idle", device4._state)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.assertEqual("idle", device1._state)
        self.assertEqual("ball_left", device2._state)
        self.assertEqual("waiting_for_ball", device3._state)
        self.assertEqual("idle", device4._state)

        self._hit_confirm()
        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)

        # ball never arrives and goes to pf. its not yet missing
        self.advance_time_and_run(10)
        self.assertEqual(0, self._missing)

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)
        self.assertEqual(None, self.machine.game)

        # ball should not be at playfield by now
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball device notices that ball went missing
        self.advance_time_and_run(100)
        self.advance_time_and_run(100)
        self.advance_time_and_run(100)
        self.advance_time_and_run(100)
        self.assertEqual(1, self._missing)

        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)
        self.assertEqual("idle", device3._state)
        self.assertEqual("idle", device4._state)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._missing)

        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

    def test_eject_successful_but_ball_never_arrives_and_stays_on_pf(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(None, self.machine.game)

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        self.assertNotEqual(None, self.machine.game)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)
        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual("idle", device1._state)
        self.assertEqual("ejecting", device2._state)
        self.assertEqual("waiting_for_ball", device3._state)
        self.assertEqual("idle", device4._state)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.assertEqual("idle", device1._state)
        self.assertEqual("ball_left", device2._state)
        self.assertEqual("waiting_for_ball", device3._state)
        self.assertEqual("idle", device4._state)

        self._hit_confirm()
        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)

        # ball never arrives and goes to pf. its not yet missing
        self.advance_time_and_run(10)
        self.assertEqual(0, self._missing)

        # ball should not be at playfield by now
        self.assertEqual(0, playfield.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball device notices that ball went missing
        self.advance_time_and_run(100)
        self.assertEqual(1, self._missing)

        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)
        self.assertEqual("idle", device3._state)
        self.assertEqual("idle", device4._state)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, self._missing)
        self.assertEqual(0, self._captured)

        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

    def test_ball_return_in_launcher(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        coil2.pulse = MagicMock()
        self._missing = 0

        self.machine.events.add_handler(
            'balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()
        coil2.pulse = MagicMock()
        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(3)

        # switch goes active again
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        assert not coil2.pulse.called

        # switch and inactive
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(3)
        assert not coil2.pulse.called

        # confirm should have failed
        self.assertEqual("failed_confirm", device2._state)

        # it comes back and the device should retry
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        self.assertEqual(0, self._captured)
