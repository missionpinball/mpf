import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestBallDeviceSwitchConfirmation(MpfTestCase):

    def __init__(self, test_map):
        super(TestBallDeviceSwitchConfirmation, self).__init__(test_map)
        self._captured = 0
        self._enter = -1
        self._missing = 0
        self._requesting = 0
        self._queue = False

    def getConfigFile(self):
        return 'test_ball_device_switch_confirmation.yaml'

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
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter', self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0


        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)
        self._captured = -1

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(1, device1.balls)
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
        self.assertEquals(0, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        self._hit_confirm()
        self.advance_time_and_run(1)

        # ball passes diverter switch
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        assert not coil_diverter.disable.called

        self.assertEquals(0, self._enter)
        self.assertEquals(-1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)


    def test_eject_no_confirm_but_target_enter(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter', self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._enter = -1
        self._captured = 0
        self._missing = 0


        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(1, device1.balls)
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
        self.assertEquals(0, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)


        # ball passes diverter switch
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called


        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)

        # eject will fail since the eject_confirm switch was not hit
        self.advance_time_and_run(30)
        self.advance_time_and_run(30)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called


        self.assertEquals(0, self._enter)
        self.assertEquals(1, self._captured)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(1, self._missing)


    def test_eject_successful_but_ball_never_arrives(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter', self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._enter = 0
        self._captured = 0
        self._missing = 0


        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(1, device1.balls)
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
        self.assertEquals(0, device1.balls)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        self._hit_confirm()
        self.advance_time_and_run(1)
        self.assertEquals(0, playfield.balls)

        # ball never arrives
        self.advance_time_and_run(300)

        # ball should be at playfield by now and got missing
        self.assertEquals(1, playfield.balls)
        self.assertEquals(1, self._missing)

        # target2 captures and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEquals(1, self._enter)
        self.assertEquals(1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._missing)


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

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0

        self.machine.ball_controller.num_balls_known = 1

        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(1, device1.balls)
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called


        self.assertEquals(None, self.machine.game)

        # start a game
        self.machine.switch_controller.process_switch("s_start", 1)
        self.advance_time_and_run(0.1)
        self.machine.switch_controller.process_switch("s_start", 0)
        self.advance_time_and_run(1)

        self.assertNotEquals(None, self.machine.game)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.balls)
        self.assertEquals(1, self.machine.ball_controller.num_balls_known)


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.balls)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.assertEquals("idle", device1._state)
        self.assertEquals("ejecting", device2._state)
        self.assertEquals("waiting_for_ball", device3._state)
        self.assertEquals("idle", device4._state)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.balls)

        self.assertEquals("idle", device1._state)
        self.assertEquals("ball_left", device2._state)
        self.assertEquals("waiting_for_ball", device3._state)
        self.assertEquals("idle", device4._state)

        self._hit_confirm()
        self.advance_time_and_run(1)
        self.assertEquals(0, playfield.balls)

        # ball never arrives and goes to pf. its not yet missing
        self.advance_time_and_run(10)
        self.assertEquals(0, self._missing)

        # ball drains
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.balls)
        self.assertEquals(None, self.machine.game)

        # ball should not be at playfield by now
        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._captured)

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball device notices that ball went missing
        self.advance_time_and_run(100)
        self.advance_time_and_run(100)
        self.advance_time_and_run(100)
        self.advance_time_and_run(100)
        self.assertEquals(1, self._missing)

        self.assertEquals("idle", device1._state)
        self.assertEquals("idle", device2._state)
        self.assertEquals("idle", device3._state)
        self.assertEquals("idle", device4._state)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._missing)

        self.assertEquals(1, self.machine.ball_controller.num_balls_known)
