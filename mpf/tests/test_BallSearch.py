from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallSearch(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_search/'

    def get_platform(self):
        return 'smart_virtual'

    def test_ball_search_does_not_start_when_disabled(self):
        self.machine.playfields.playfield.config['enable_ball_search'] = False

        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        self.advance_time_and_run(30)
        self.assertFalse(self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertFalse(self.machine.ball_devices['playfield'].ball_search.started)

        self.machine.playfields.playfield.config['enable_ball_search'] = None
        self.machine.config['mpf']['default_ball_search'] = True
        self.machine.ball_devices['playfield'].ball_search.enable()
        self.assertTrue(self.machine.ball_devices['playfield'].ball_search.enabled)
        self.machine.ball_devices['playfield'].ball_search.disable()
        self.assertFalse(self.machine.ball_devices['playfield'].ball_search.enabled)

        self.machine.playfields.playfield.config['enable_ball_search'] = None
        self.machine.config['mpf']['default_ball_search'] = False
        self.machine.ball_devices['playfield'].ball_search.enable()
        self.assertFalse(self.machine.ball_devices['playfield'].ball_search.enabled)

    def test_game_with_no_switches(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        # wait for eject_timeout of launcher
        self.advance_time_and_run(6)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)

        # vuk should reset the timer
        self.machine.switch_controller.process_switch("s_vuk", 1)
        # wait for eject_timeout of vuk
        self.advance_time_and_run(3)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

        self.advance_time_and_run(15)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.advance_time_and_run(5)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

    def test_game_with_switches(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(2)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)

        # vuk should reset the timer
        self.machine.switch_controller.process_switch("s_vuk", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.machine.servos.servo1.go_to_position(0.7)

        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

        self.advance_time_and_run(15)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.advance_time_and_run(5)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        # test servo
        self.assertEqual(0.0, self.machine.servos.servo1.hw_servo.current_position)
        self.advance_time_and_run(5)
        self.assertEqual(1.0, self.machine.servos.servo1.hw_servo.current_position)
        self.advance_time_and_run(5)
        self.assertEqual(0.0, self.machine.servos.servo1.hw_servo.current_position)

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

        # servo should return to its position
        self.assertEqual(0.7, self.machine.servos.servo1.hw_servo.current_position)

    def test_ball_search_iterations_and_give_up_with_new_ball(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(2)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(.1)

        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)

        # push down target 3 and 4
        self.machine.switch_controller.process_switch("s_drop_target3", 1)
        self.machine.switch_controller.process_switch("s_drop_target4", 1)

        self.advance_time_and_run(10.1)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)

        self.machine.ball_devices['playfield'].add_ball = MagicMock()

        for i in range(1, 11):
                # this will break smart_virtual
                self.machine.coils['eject_coil1'].pulse = MagicMock()
                self.machine.coils['eject_coil2'].pulse = MagicMock()
                self.machine.coils['eject_coil3'].pulse = MagicMock()
                self.machine.coils['hold_coil'].pulse = MagicMock()
                self.machine.coils['drop_target_reset1'].pulse = MagicMock()
                self.machine.coils['drop_target_reset2'].pulse = MagicMock()
                self.machine.coils['drop_target_reset3'].pulse = MagicMock()
                self.machine.coils['drop_target_reset4'].pulse = MagicMock()
                self.machine.coils['drop_target_knockdown2'].pulse = MagicMock()
                self.machine.coils['drop_target_knockdown4'].pulse = MagicMock()
                self.advance_time_and_run(10)
                if i <= 3:
                    self.assertEqual(1, self.machine.ball_devices['playfield'].ball_search.phase)
                elif i <= 6:
                    self.assertEqual(2, self.machine.ball_devices['playfield'].ball_search.phase)
                else:
                    self.assertEqual(3, self.machine.ball_devices['playfield'].ball_search.phase)
                self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

                assert not self.machine.coils['eject_coil1'].pulse.called
                if 3 < i <= 6:
                    self.machine.coils['eject_coil2'].pulse.assert_called_with(5)
                else:
                    self.machine.coils['eject_coil2'].pulse.assert_called_with()
                assert not self.machine.coils['eject_coil3'].pulse.called
                assert not self.machine.coils['hold_coil'].pulse.called
                assert not self.machine.coils['drop_target_reset1'].pulse.called
                assert not self.machine.coils['drop_target_reset2'].pulse.called
                assert not self.machine.coils['drop_target_knockdown2'].pulse.called

                self.advance_time_and_run(.25)

                assert not self.machine.coils['eject_coil1'].pulse.called
                self.machine.coils['eject_coil3'].pulse.assert_called_with()
                assert not self.machine.coils['hold_coil'].pulse.called
                assert not self.machine.coils['drop_target_reset1'].pulse.called
                assert not self.machine.coils['drop_target_reset2'].pulse.called
                assert not self.machine.coils['drop_target_knockdown2'].pulse.called

                self.advance_time_and_run(.25)

                assert not self.machine.coils['eject_coil1'].pulse.called
                self.machine.coils['hold_coil'].pulse.assert_called_with()
                assert not self.machine.coils['drop_target_reset1'].pulse.called
                assert not self.machine.coils['drop_target_reset2'].pulse.called
                assert not self.machine.coils['drop_target_knockdown2'].pulse.called

                self.advance_time_and_run(.25)

                assert not self.machine.coils['eject_coil1'].pulse.called
                self.machine.coils['drop_target_reset1'].pulse.assert_called_with()
                assert not self.machine.coils['drop_target_reset2'].pulse.called
                assert not self.machine.coils['drop_target_knockdown2'].pulse.called

                self.advance_time_and_run(.25)

                assert not self.machine.coils['eject_coil1'].pulse.called
                if i <= 3:
                    self.machine.coils['drop_target_reset2'].pulse.assert_called_with()
                    assert not self.machine.coils['drop_target_knockdown2'].pulse.called
                else:
                    self.machine.coils['drop_target_reset2'].pulse.assert_called_with()
                    self.machine.coils['drop_target_knockdown2'].pulse.assert_called_with()

                assert not self.machine.coils['drop_target_reset3'].pulse.called
                assert not self.machine.coils['drop_target_reset4'].pulse.called
                assert not self.machine.coils['drop_target_knockdown4'].pulse.called

                if i > 6:
                    self.advance_time_and_run(.25)
                    self.machine.coils['drop_target_reset3'].pulse.assert_called_with()

                self.advance_time_and_run(.25)
                if i <= 3:
                    self.machine.coils['drop_target_knockdown4'].pulse.assert_called_with()
                    assert not self.machine.coils['drop_target_reset4'].pulse.called
                else:
                    self.machine.coils['drop_target_reset4'].pulse.assert_called_with()
                    self.machine.coils['drop_target_knockdown4'].pulse.assert_called_with()

                assert not self.machine.ball_devices['playfield'].add_ball.called

        self.advance_time_and_run(10)

        self.assertEqual(0, self.machine.ball_devices['playfield'].balls)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.started)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.machine.ball_devices['playfield'].add_ball.assert_called_with()

    def test_give_up_with_game_end_in_game(self):
        self.machine.ball_devices['playfield'].config['ball_search_failed_action'] = 'end_game'

        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        self.advance_time_and_run(30)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        # wait for ball search to fail
        self.advance_time_and_run(300)
        self.assertEqual(0, self.machine.ball_devices['playfield'].balls)
        self.assertEqual(None, self.machine.game)

    def test_give_up_with_game_end_outside_game(self):
        self.machine.ball_devices['playfield'].config['ball_search_failed_action'] = 'end_game'

        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.machine.switch_controller.process_switch("s_ball_switch3", 1)
        self.advance_time_and_run(1)

        self.assertEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        # add a random ball to the pf via vuk
        self.machine.switch_controller.process_switch("s_vuk", 1)
        self.advance_time_and_run(30)

        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        # try to start a game (should not work)
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertEqual(None, self.machine.game)

        # wait for ball search to fail
        self.advance_time_and_run(300)
        self.assertEqual(None, self.machine.game)
        self.assertEqual(0, self.machine.ball_devices['playfield'].balls)
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        # try to start a game (should work again)
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)

    def test_give_up_with_no_more_balls(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

        self.assertEqual(None, self.machine.game)
        self.machine.switch_controller.process_switch("s_start", 1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)
        self.assertNotEqual(None, self.machine.game)
        self.assertEqual(False, self.machine.ball_devices['playfield'].ball_search.enabled)

        self.machine.coils['eject_coil1'].pulse = MagicMock()
        self.machine.coils['eject_coil2'].pulse = MagicMock()
        self.machine.coils['eject_coil3'].pulse = MagicMock()
        self.machine.coils['hold_coil'].pulse = MagicMock()

        self.advance_time_and_run(10)
        self.assertEqual(1, self.machine.ball_devices['playfield'].balls)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.enabled)
        self.advance_time_and_run(30)
        self.assertEqual(True, self.machine.ball_devices['playfield'].ball_search.started)

        # wait for ball search to fail
        self.advance_time_and_run(150)
        self.assertEqual(0, self.machine.ball_devices['playfield'].balls)
        self.assertEqual(0, self.machine.ball_controller.num_balls_known)
        self.assertEqual(None, self.machine.game)
