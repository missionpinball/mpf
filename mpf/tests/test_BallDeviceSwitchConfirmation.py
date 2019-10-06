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

    def get_config_file(self):
        return 'test_ball_device_switch_confirmation.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def _missing_ball(self, **kwargs):
        del kwargs
        self._missing += 1

    def _requesting_ball(self, balls, **kwargs):
        del kwargs
        self._requesting += balls

    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        del new_balls
        del kwargs
        self._enter += unclaimed_balls

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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        self.assertTrue(coil1.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(0, self._enter)
        self.assertEqual(-1, self._captured)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, self._missing)

    def test_eject_no_confirm_but_target_enter(self):
        # TODO: we may detect this problem and act accordingly (broken confirm switch)
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
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._enter = -1
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0

        # assume we have more than one ball to prevent BallController from "fixing" pf
        self.machine.ball_controller.num_balls_known = 5

        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
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
        self.assertEqual(-1, playfield.available_balls)
        self.assertEqual(-1, playfield.balls)

        # eject will fail since the eject_confirm switch was not hit
        self.advance_time_and_run(100)

        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEqual(0, self._enter)
        self.assertEqual(1, self._captured)

        # no ball on pf because the pf saw an unexpected ball
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)
        self.assertEqual(1, self._missing)

        # there should be exactly 2 available_balls in the machine
        self.assertEqual(0, device1.available_balls)
        self.assertEqual(0, device2.available_balls)
        self.assertEqual(2, device4.available_balls)
        self.assertEqual(0, playfield.available_balls)

    def test_eject_successful_but_ball_never_arrives(self):
        # TODO: improve this situation
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
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self._hit_confirm()
        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        # ball never arrives
        self.advance_time_and_run(20)

        # ball should be at playfield by now and got missing
        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, self._missing)

        # since target2 != playfield. we eject a new ball to target2
        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self._hit_confirm()
        self.advance_time_and_run(1)

        # target2 captures and keeps ball
        self.machine.switch_controller.process_switch(
            "s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device4.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # there should be exactly 2 available_balls in the machine
        self.assertEqual(0, device1.available_balls)
        self.assertEqual(0, device2.available_balls)
        self.assertEqual(1, device4.available_balls)
        self.assertEqual(1, playfield.available_balls)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(1, playfield.balls)
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
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._captured = 0
        self._missing = 0

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0

        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
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
        self.assertEqual(2, device1.balls)
        self.assertEqual(None, self.machine.game)

        # ball should not be at playfield by now
        self.assertEqual(-1, playfield.balls)
        self.assertEqual(1, self._captured)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball device notices that ball went missing
        self.advance_time_and_run(100)

        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)
        self.assertEqual("idle", device3._state)
        self.assertEqual("idle", device4._state)

        # there should be exactly 2 available_balls in the machine
        self.assertEqual(2, device1.available_balls)
        self.assertEqual(0, device2.available_balls)
        self.assertEqual(0, device3.available_balls)
        self.assertEqual(0, device4.available_balls)
        self.assertEqual(0, playfield.available_balls)

        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._missing)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)

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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        self.assertTrue(coil1.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball device notices that ball went missing
        self.advance_time_and_run(100)
        self.assertEqual(1, self._missing)

        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)
        self.assertEqual("idle", device3._state)
        self.assertEqual("idle", device4._state)

        # there should be exactly 1 available_ball in the machine
        self.assertEqual(0, device1.available_balls)
        self.assertEqual(0, device2.available_balls)
        self.assertEqual(0, device3.available_balls)
        self.assertEqual(0, device4.available_balls)
        self.assertEqual(1, playfield.available_balls)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, self._missing)
        self.assertEqual(0, self._captured)

        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

    def test_ball_return_in_launcher(self):
        # add two initial balls to trough
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.assertEqual(2, self.machine.ball_devices["test_trough"].balls)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertBallsOnPlayfield(0, "playfield")
        self.assertAvailableBallsOnPlayfield(0, "playfield")

        self.hit_switch_and_run("s_ball_switch_target1", 1)

        self.release_switch_and_run("s_ball_switch_target1", 1)
        self.assertBallsOnPlayfield(0, "playfield")
        self.assertAvailableBallsOnPlayfield(1, "playfield")

        self.machine.ball_devices["test_target1"].request_ball()
        self.assertEqual(1, self.machine.ball_devices["test_target1"].available_balls)

        self.advance_time_and_run()
        self.assertEqual("pulsed_10", self.machine.coils["eject_coil1"].hw_driver.state)
        self.release_switch_and_run("s_ball_switch2", 1)
        self.advance_time_and_run(8)

        self.hit_switch_and_run("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        self.assertEqual("pulsed_10", self.machine.coils["eject_coil2"].hw_driver.state)
        self.machine.coils["eject_coil2"].hw_driver.state = None

        # it leaves the switch
        self.release_switch_and_run("s_ball_switch_launcher", 3)

        # switch goes active again
        self.hit_switch_and_run("s_ball_switch_launcher", 1)
        self.assertEqual(None, self.machine.coils["eject_coil2"].hw_driver.state)
        self.assertEqual(1, self.machine.ball_devices["test_target1"].available_balls)

        self.advance_time_and_run(9)
        self.assertEqual("pulsed_10", self.machine.coils["eject_coil2"].hw_driver.state)
        self.assertEqual(1, self.machine.ball_devices["test_target1"].available_balls)

        self.release_switch_and_run("s_ball_switch_launcher", 1)

        self._hit_confirm()
        self.advance_time_and_run()

        self.hit_switch_and_run("s_ball_switch_target1", 1)

        self.assertBallsOnPlayfield(1, "playfield")
        self.assertAvailableBallsOnPlayfield(1, "playfield")
