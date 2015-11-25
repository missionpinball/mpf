import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestBallLock(MpfTestCase):

    def getConfigFile(self):
        return 'test_ball_lock.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_device/'

    def _missing_ball(self):
        self._missing += 1

    def _ball_enter(self, new_balls, unclaimed_balls, **kwargs):
        self._enter += new_balls

    def _captured_from_pf(self, balls, **kwargs):
        self._captured += balls

    def _captured_from_pf(self, balls, **kwargs):
        self._captured += balls

    def _collecting_balls_complete_handler(self, **kwargs):
        self._collecting_balls_complete = 1

    def test_lock_and_release_at_game_end(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        lock = self.machine.ball_devices['test_lock']
        lock_logic = self.machine.ball_locks['lock_test']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete', self._collecting_balls_complete_handler)


        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0
        self.machine.ball_controller.num_balls_known = 2

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0
        self.assertEquals(0, playfield.balls)
        self.assertEquals(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEquals(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        # trough ejects
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, trough.balls)


        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, launcher.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, launcher.balls)

        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # ball enters lock 
        self.machine.switch_controller.process_switch("s_ball_switch_lock1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, lock.balls)

        # it will request another ball
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(1, lock_logic.balls_locked)
        self._captured = 0

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, trough.balls)


        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, launcher.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, launcher.balls)

        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)

        # ball drains and game ends
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self._captured = 0
        self.assertEquals(2, self.machine.ball_controller.num_balls_known)

        # lock should eject all balls
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil3.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch_lock1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, lock.balls)
        self.assertEquals(0, lock_logic.balls_locked)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)

        self.assertEquals(0, self._collecting_balls_complete)

        # ball also drains
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)

        self.assertEquals(2, self.machine.ball_controller.num_balls_known)
        self.assertEquals(1, self._collecting_balls_complete)

        self.advance_time_and_run(100)
        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)

        self.assertEquals(2, self.machine.ball_controller.num_balls_known)
        self.assertEquals(1, self._collecting_balls_complete)


    def test_lock_full_and_release(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        lock = self.machine.ball_devices['test_lock']
        lock_logic = self.machine.ball_locks['lock_test']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete', self._collecting_balls_complete_handler)

        lock_logic.enable()

        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0
        self.machine.ball_controller.num_balls_known = 2

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0
        self.assertEquals(0, playfield.balls)
        self.assertEquals(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEquals(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        self.assertFalse(lock_logic.is_full())
        self.assertEquals(2, trough.available_balls)

        # lock captures a first random ball
        self.machine.switch_controller.process_switch("s_ball_switch_lock1", 1)
        self.advance_time_and_run(1)
        assert not coil3.pulse.called
        self.assertFalse(lock_logic.is_full())
        self.assertFalse(lock.is_full())
        self.assertEquals(1, trough.available_balls)

        # lock captures a second random ball
        self.machine.switch_controller.process_switch("s_ball_switch_lock2", 1)
        self.advance_time_and_run(1)
        assert not coil3.pulse.called
        self.assertTrue(lock_logic.is_full())
        self.assertFalse(lock.is_full())
        self.assertEquals(0, trough.available_balls)

        # lock captures a third random ball
        self.machine.switch_controller.process_switch("s_ball_switch_lock3", 1)
        self.advance_time_and_run(1)

        # it should eject it right away
        coil3.pulse.assert_called_once_with()
        self.assertTrue(lock_logic.is_full())
        self.assertTrue(lock.is_full())
        self.advance_time_and_run(1)

        self.machine.switch_controller.process_switch("s_ball_switch_lock3", 0)
        self.advance_time_and_run(.1)
        self.assertTrue(lock_logic.is_full())
        self.assertFalse(lock.is_full())

    def test_eject_to_lock(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        trough = self.machine.ball_devices['test_trough']
        launcher = self.machine.ball_devices['test_launcher']
        lock = self.machine.ball_devices['test_lock']
        lock_logic = self.machine.ball_locks['lock_test']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('collecting_balls_complete', self._collecting_balls_complete_handler)


        self._enter = 0
        self._captured = 0
        self._missing = 0
        self._collecting_balls_complete = 0
        self.machine.ball_controller.num_balls_known = 2

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0
        self.assertEquals(0, playfield.balls)
        self.assertEquals(2, self.machine.ball_controller.num_balls_known)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEquals(2, trough.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        # trough ejects
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, trough.balls)


        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, launcher.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, launcher.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # ball directly enters the lock 
        self.machine.switch_controller.process_switch("s_ball_switch_lock1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, lock.balls)

        # it will request another ball
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(1, lock_logic.balls_locked)
        self._captured = 0

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, trough.balls)


        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, launcher.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, launcher.balls)

        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(1, lock.available_balls)

        # request a release of one ball from lock via event
        self.machine.events.post("release_test")
        # since we are not using a multi ball increase the balls_in_play manually
        self.assertEquals(1, self.machine.game.balls_in_play)
        self.machine.game.balls_in_play += 1
        self.advance_time_and_run(1)

        # lock should eject a ball
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil3.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch_lock1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, lock.balls)
        self.assertEquals(0, lock_logic.balls_locked)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)

        # ball drains instantly. one left on pf
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self.machine.game.balls_in_play)

        # other ball hits some pf switches
        self.machine.switch_controller.process_switch("s_playfield_active", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_playfield_active", 0)
        self.advance_time_and_run(1)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self._captured = 0
        self.assertEquals(2, self.machine.ball_controller.num_balls_known)

        self.assertEquals(0, self._collecting_balls_complete)
        self.assertEquals(1, self.machine.game.balls_in_play)


        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # we add another ball
        self.machine.game.balls_in_play += 1
        playfield.add_ball()
        self.advance_time_and_run(1)
        self.assertEquals(2, self.machine.game.balls_in_play)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, trough.balls)

        # launcher receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, launcher.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # launcher shoots the ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, launcher.balls)

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # ball directly enters the lock (again)
        self.machine.switch_controller.process_switch("s_ball_switch_lock1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, lock.balls)

        # playfield count goes to 0
        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self._captured = 0

        # wait for eject confirm for lock
        self.advance_time_and_run(10)

        # theoretically it would eject another ball but there is no ball in the trough
        self.assertEquals(1, len(launcher.ball_requests)) 

        self.assertEquals(2, self.machine.ball_controller.num_balls_known)

        self.advance_time_and_run(100)
        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)

        self.assertEquals(2, self.machine.ball_controller.num_balls_known)

