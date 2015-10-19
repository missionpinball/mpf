import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestBallDevice(MpfTestCase):

    def __init__(self, test_map):
        super(TestBallDevice, self).__init__(test_map)
        self._captured = -1
        self._enter = -1
        self._missing = 0
        self._requesting = 0

    def getConfigFile(self):
        return 'test_ball_device.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_device/'


    def _missing_ball(self):
        self._missing += 1

    def test_ball_count_during_eject(self):
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)

        self._missing = 0

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())

        coil2.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)

        self.assertEquals(0, self._missing)

    def _requesting_ball(self, balls, **kwargs):
        self._requesting += balls

    def test_ball_eject_failed(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        # launcher should retry eject
        self.advance_time_and_run(20)
        coil2.pulse.assert_called_twice_with()

        self.assertEquals(0, self._requesting)

    def test_eject_successful_to_playfield(self):
        pass
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        deverter = self.machine.diverters['d_test']
        playfield = self.machine.ball_devices['playfield']
        
        # add an initial ball to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(1, device1.count_balls())
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.count_balls())


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.count_balls())

        # ball passes diverter switch
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        #coil_diverter.disable.assert_called_once_with()
        assert not coil_diverter.enable.called
        
        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.count_balls())
        
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        coil3.pulse.assert_called_once_with()
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.count_balls())

        self.assertEquals(1, playfield.balls)


    def _ball_enter(self, balls, **kwargs):
        self._enter = balls

    def _captured_from_pf(self, balls, **kwargs):
        self._captured = balls


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
        deverter = self.machine.diverters['d_test']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_test_target2_ball_enter', self._ball_enter)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._enter = -1
        self._captured = -1
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
        self.assertEquals(1, device1.count_balls())
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
        self.assertEquals(0, device1.count_balls())


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.count_balls())

        # ball passes diverter switch
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called
        
        # target2 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.count_balls())
        
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        assert not coil_diverter.disable.called

        self.assertEquals(0, self._enter)
        self.assertEquals(-1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)

