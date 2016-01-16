import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time


class TestBallDeviceManualWithCount(MpfTestCase):
    def __init__(self, test_map):
        super().__init__(test_map)
        self._captured = 0
        self._enter = 0
        self._missing = 0
        self._requesting = 0
        self._queue = False

    def getConfigFile(self):
        return 'test_ball_device_manual_with_count.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_device/'

    def _missing_ball(self):
        self._missing += 1

    def _requesting_ball(self, balls, **kwargs):
        self._requesting += balls

    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        self._enter += new_balls

    def _captured_from_pf(self, balls, **kwargs):
        self._captured += balls

    def test_manual_successful_eject_to_pf(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

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
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request a ball
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        # player shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

    def test_manual_with_retry_to_pf(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

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

        # trough should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request a ball to the playfield
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(.1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)

        self.assertEqual(0, device1.balls)

        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        # player shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(0.1)

        # too soft and it comes back
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(10)
        self.assertEqual(1, device2.balls)
        assert not coil2.pulse.called

        # player drinks his coffee
        self.advance_time_and_run(300)

        # player shoots the ball again
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)
        assert not coil2.pulse.called

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)

        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

    def test_trough_retry(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0
        self.machine.ball_controller.num_balls_known = 1

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(0.1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        # ball falls back
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # it retries after a timeout
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        # trough ejects again
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        # player shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(0.1)

        # too soft and it comes back
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(11)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        # player drinks his coffee
        self.advance_time_and_run(300)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        # player shoots the ball again
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)

        self.advance_time_and_run(100)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual(1, self.machine.ball_controller.num_balls_known)

    def test_manual_fast_skipping_successful_eject_to_pf(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
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
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher does not see the ball. player ejects it right away
        self.advance_time_and_run(1)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        # ball hits the playfield
        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # will request a second ball. launcher has to use count eject confirmation
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher does not see the ball. player ejects it right away
        self.advance_time_and_run(1)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        self.assertEqual(1, playfield.balls)
        # since it will use count as eject confirm we have to wait for eject_timout of both devices
        self.advance_time_and_run(6 + 3)

        self.assertEqual(2, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEqual(2, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)

    def test_capture_random_ball(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # launcher receives a random ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil2.pulse.assert_called_once_with()

        # launcher should eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)

    def test_manual_ball_missing(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        target = self.machine.ball_devices['test_target']
        playfield = self.machine.ball_devices['playfield']

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
        self.assertEqual(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball
        playfield.add_ball(source_device=target, player_controlled=True)
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.assertEqual(1, len(target.eject_queue))
        self.assertEqual(0, len(target._incoming_balls))

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        self.assertEqual(1, len(target.eject_queue))
        self.assertEqual(1, len(target._incoming_balls))
        self.advance_time_and_run(10)

        self.assertEqual(1, len(target.eject_queue))
        self.assertEqual(1, len(target._incoming_balls))

        # it does not hit any playfield switches and goes missing
        self.advance_time_and_run(100)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(1, self._missing)
        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)
        self.assertEqual("idle", target._state)

    def test_trough_eject_failed_with_manual(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
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

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(0.1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        # and it comes back
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # wait until timeout reached
        self.advance_time_and_run(1)
        self.assertEqual(2, device1.balls)

        # trough ejects again
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)
        self.assertEqual("idle", device1._state)

        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # player shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.advance_time_and_run(10)

        assert not coil1.pulse.called
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)

        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        assert not coil1.pulse.called
        assert not coil2.pulse.called

        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)

    def test_manual_successful_eject_with_no_pf_switch_hit(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0
        self.machine.ball_controller.num_balls_known = 2

        # add two initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        # player shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        # it hits the pf but no pf switch (not confirmed yet)
        self.advance_time_and_run(1)
        #        self.assertEquals(0, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        # it drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEqual(2, self.machine.ball_controller.num_balls_known)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, self._captured)
        self.assertEqual(0, self._missing)

    #    def _launcher_eject_attempt(self, balls, **kwargs):
    #        self._launcher_eject_attempt += balls

    def test_request_to_pf_and_launcher_and_unexpected_manual_eject(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        #        self.machine.events.add_handler('balldevice_test_launcher_ball_eject_attempt', self._launcher_eject_attempt)
        self._enter = 0
        self._captured = 0
        self._missing = 0
        #        self._launcher_eject_attempt = 0


        # add two initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball to pf
        playfield.add_ball(player_controlled=False)
        self.advance_time_and_run(1)

        # request an ball to launcher
        device2.request_ball()

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)
        # one for mechanical eject and one for the "real" attempt
        #        self.assertEquals(2, self._launcher_eject_attempt)
        #        self._launcher_eject_attempt = 0


        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)
        # launcher should be idle
        self.assertEqual("idle", device2._state)

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        self.advance_time_and_run(100)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        # since we have a mechanical plunger the player decides to eject the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, self._captured)

        # both balls drain (before confirm of the second)
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self._captured)
        self.assertEqual(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEqual(0, self._missing)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(2, self._captured)
        # launcher should be idle
        self.assertEqual("idle", device2._state)

    def test_request_to_launcher_and_pf(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # add two initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball to launcher
        device2.request_ball()

        # request an ball to pf
        playfield.add_ball(player_controlled=False)
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        # thats it. no more ejects.
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        self.advance_time_and_run(100)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

    def test_request_launcher_with_manual_eject_and_skip(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # add two initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball to launcher
        device2.request_ball()
        self.advance_time_and_run(0.1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # it skips launcher and goes to pf
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        # no launcher eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        self.advance_time_and_run(100)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)
        self.assertEqual("idle", device2._state)

    def test_request_manual_when_launcher_has_ball(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # add two initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEqual(2, self._captured)
        self._captured = 0
        self.assertEqual(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(2, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # request an ball to launcher
        device2.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        # ball stays in launcher
        coil1.pulse.assert_called_once_with()
        coil1.pulse = MagicMock()
        assert not coil2.pulse.called

        # request an ball to pf
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # still no eject. waiting for player
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        # player shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        # thats it. no more ejects.
        assert not coil1.pulse.called
        assert not coil2.pulse.called

        self.advance_time_and_run(100)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)
