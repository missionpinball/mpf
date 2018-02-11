from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestBallDeviceManualWithTarget(MpfTestCase):
    def __init__(self, test_map):
        super().__init__(test_map)
        self._captured = 0
        self._enter = 0
        self._missing = 0
        self._requesting = 0
        self._queue = False

    def getConfigFile(self):
        return 'test_ball_device_manual_with_target.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def _missing_ball(self, **kwargs):
        del kwargs
        self._missing += 1

    def _requesting_ball(self, balls, **kwargs):
        del kwargs
        self._requesting += balls

    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        del kwargs
        del unclaimed_balls
        self._enter += new_balls

    def _captured_from_pf(self, balls, **kwargs):
        del kwargs
        self._captured += balls

    def test_manual_successful_eject_to_pf(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)

        self.assertEqual(0, device1.balls)

        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(0.1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
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
        self.advance_time_and_run(2)
        self.assertEqual(1, device1.balls)
        self.assertTrue(coil1.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        # player drinks his coffee
        self.advance_time_and_run(300)

        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        # player shoots the ball again
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device2.balls)

        self.assertTrue(coil1.pulse.called)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        # playfield but count is not increased because eject_timeout of trough did not expire yet
        self.hit_and_release_switch("s_playfield")
        self.assertEqual(0, playfield.balls)

        # launcher does not see the ball. player ejects it right away. timeout expires
        self.advance_time_and_run(3)

        # ball hits the playfield (again)
        self.hit_and_release_switch("s_playfield")
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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        # launcher does not see the ball. player ejects it right away
        self.advance_time_and_run(1)

        self.assertTrue(coil1.pulse.called)
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
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_captured_from_playfield',
                                        self._captured_from_pf)
        self.machine.events.add_handler('balldevice_ball_missing',
                                        self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0

        # launcher receives a random ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil2.pulse.called)

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
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        target = self.machine.ball_devices['test_target']
        playfield = self.machine.ball_devices['playfield']

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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.assertEqual(playfield, target.outgoing_balls_handler._current_target)
        self.assertEqual(0, len(target.incoming_balls_handler._incoming_balls))

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, device1.balls)

        self.assertEqual(playfield, target.outgoing_balls_handler._current_target)
        self.advance_time_and_run(10)

        self.assertEqual(playfield, target.outgoing_balls_handler._current_target)

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
        self.assertTrue(coil1.pulse.called)
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
        self.advance_time_and_run(2)
        self.assertEqual(2, device1.balls)

        # trough ejects again
        self.assertTrue(coil1.pulse.called)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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

        # request an ball
        playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives but waits for player to eject
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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

        # request an ball to pf
        playfield.add_ball(player_controlled=False)
        self.advance_time_and_run(1)

        # request an ball to launcher
        device2.request_ball()

        # trough eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
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

        # trough eject
        self.assertTrue(coil1.pulse.called)
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

        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        self.advance_time_and_run(100)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, playfield.available_balls)
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
        self.assertEqual(0, playfield.available_balls)
        self.assertEqual(2, self._captured)
        self.assertEqual(0, self._missing)

        self.advance_time_and_run(100)
        self.assertEqual(0, self._missing)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(0, playfield.available_balls)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # launcher receives
        self.machine.switch_controller.process_switch("s_ball_switch_launcher",
                                                      1)
        self.advance_time_and_run(1)
        self.assertEqual(1, device2.balls)

        self.assertTrue(coil1.pulse.called)
        self.assertTrue(coil2.pulse.called)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEqual(1, device1.balls)

        # it skips launcher and goes to pf
        self.advance_time_and_run(3)

        self.machine.switch_controller.process_switch("s_playfield", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, playfield.available_balls)

        # no launcher eject
        self.assertTrue(coil1.pulse.called)
        assert not coil2.pulse.called
        self.advance_time_and_run(100)

        self.assertEqual(1, playfield.balls)
        self.assertEqual(1, playfield.available_balls)
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
        self.machine.events.add_handler('balldevice_ball_missing',
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
        self.assertEqual(0, playfield.available_balls)

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
        self.assertTrue(coil1.pulse.called)
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
        self.assertTrue(coil1.pulse.called)
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
        self.assertEqual(1, playfield.available_balls)
        self.assertEqual(0, self._captured)
        self.assertEqual(0, self._missing)

        self.assertEqual("idle", device1._state)
        self.assertEqual("idle", device2._state)

    def test_launcher_without_auto_fire_on_unexpected_ball(self):
        coil4 = self.machine.coils['eject_coil4']
        launcher_manual = self.machine.ball_devices['test_launcher_manual_on_unexpected']
        playfield = self.machine.ball_devices['playfield']

        # add ball to pf
        self.machine.ball_controller.num_balls_known = 1
        playfield.balls = 1
        playfield.available_balls = 1
        self.assertEqual(1, playfield.balls)
        coil4.pulse = MagicMock()
        self.assertEqual(0, launcher_manual.balls)
        assert not coil4.pulse.called

        # ball enters the launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher2", 1)
        self.advance_time_and_run(1)

        # it should stay there and wait for manual eject
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, launcher_manual.balls)
        self.assertEqual("ejecting", launcher_manual._state)
        assert not coil4.pulse.called

        # player has time
        self.advance_time_and_run(100)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, launcher_manual.balls)
        self.assertEqual("ejecting", launcher_manual._state)
        assert not coil4.pulse.called

        # but finally he ejects the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher2", 0)
        self.advance_time_and_run(1)
        self.assertEqual("ball_left", launcher_manual._state)
        self.advance_time_and_run(20)
        self.assertEqual("idle", launcher_manual._state)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, launcher_manual.balls)

    def test_vuk_with_auto_fire_on_unexpected_ball_false(self):
        coil5 = self.machine.coils['eject_coil5']
        vuk = self.machine.ball_devices['test_vuk']
        coil2 = self.machine.coils['eject_coil2']
        launcher = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']

        # add ball to pf
        self.machine.ball_controller.num_balls_known = 1
        playfield.balls = 1
        playfield.available_balls = 1
        coil5.pulse = MagicMock()
        coil2.pulse = MagicMock()
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, launcher.balls)
        self.assertEqual(0, vuk.balls)
        assert not coil5.pulse.called
        assert not coil2.pulse.called

        # ball enters launcher unexpectedly
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, launcher.balls)

        # launcher auto fires
        self.assertTrue(coil2.pulse.called)
        coil2.pulse = MagicMock()

        # ball leaves
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)

        # ball is back on pf
        self.advance_time_and_run(10)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, launcher.balls)

        # ball enters the vuk
        self.machine.switch_controller.process_switch("s_vuk", 1)
        self.advance_time_and_run(1)

        # vuk ejects to launcher
        self.assertTrue(coil5.pulse.called)
        coil5.pulse = MagicMock()

        # ball leaves
        self.machine.switch_controller.process_switch("s_vuk", 0)
        self.advance_time_and_run(1)

        # and enters launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, launcher.balls)
        self.assertEqual(0, vuk.balls)

        # it should stay there and wait for manual eject
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, launcher.balls)
        self.assertEqual("ejecting", launcher._state)
        assert not coil2.pulse.called

        # player has time
        self.advance_time_and_run(100)
        self.assertEqual(0, playfield.balls)
        self.assertEqual(1, launcher.balls)
        self.assertEqual("ejecting", launcher._state)
        assert not coil2.pulse.called

        # but finally he ejects the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEqual("ball_left", launcher._state)
        self.advance_time_and_run(20)
        self.assertEqual("idle", launcher._state)
        self.assertEqual("idle", vuk._state)
        self.assertEqual(1, playfield.balls)
        self.assertEqual(0, launcher.balls)
        self.assertEqual(0, vuk.balls)
