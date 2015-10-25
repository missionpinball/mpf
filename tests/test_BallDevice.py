import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestBallDevice(MpfTestCase):

    def __init__(self, test_map):
        super(TestBallDevice, self).__init__(test_map)
        self._captured = 0
        self._enter = -1
        self._missing = 0
        self._requesting = 0
        self._queue = False

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
        self.advance_time_and_run(10000)
        self.advance_time_and_run(10000)
        self.assertEquals(1, self._missing)


    def _requesting_ball(self, balls, **kwargs):
        self._requesting += balls

    def test_ball_eject_failed(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        self._captured = 0

        # launcher should retry eject
        self.advance_time_and_run(20)
        coil2.pulse.assert_called_twice_with()

        self.assertEquals(0, self._requesting)


        # it should not claim a ball which enters the target
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, self._captured)

#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
#        self.advance_time_and_run(300)
        self.advance_time_and_run(10000)

    def test_ball_eject_timeout_and_late_confirm(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()
        self._missing = 0

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()
        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        # but not confirm. eject timeout = 6s
        self.advance_time_and_run(15)
        coil2.pulse.assert_called_once_with()

        # late confirm
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, self._requesting)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, self._captured)

    def test_ball_left_and_return_failure(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()
        self._missing = 0

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()
        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        # it comes back (before timeout)
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()

        # retry after timeout
        self.advance_time_and_run(4)
        coil2.pulse.assert_called_twice_with()

        self.assertEquals(0, self._captured)

        # ball did not leave the launcher (it returned). target should capture
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, self._requesting)
        self.assertEquals(0, self._missing)
        self.assertEquals(1, self._captured)


    def test_ball_eject_timeout_and_ball_missing(self):
        self._requesting = 0
        coil2 = self.machine.coils['eject_coil2']
        device2 = self.machine.ball_devices['test_launcher']
        playfield = self.machine.ball_devices['playfield']
        coil2.pulse = MagicMock()
        self._missing = 0
        self._captured = 0
        self._enter = 0

        self.machine.events.add_handler('balldevice_test_launcher_ball_request', self._requesting_ball)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_test_target1_ball_enter', self._ball_enter)

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        # launcher should eject
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_once_with()
        self.assertEquals(1, self._captured)

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)

        # but not confirm. eject timeout = 6s
        self.advance_time_and_run(15)
        coil2.pulse.assert_called_once_with()

        self.advance_time_and_run(30)

        self.assertEquals(1, self._requesting)
        self.assertEquals(1, self._missing)
        self.assertEquals(1, playfield.balls)

        self._missing = 0
        self._requesting = 0
        self._captured = 0

        # target1 captures a ball since the eject failed
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)

        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, playfield.balls)

        # and ejects it
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, playfield.balls)

        self._captured = 0


        # launcher captures a ball and should retry
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        coil2.pulse.assert_called_twice_with()

        self.assertEquals(1, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, playfield.balls)

        self._captured = 0

        # it leaves the switch
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)


        # and reaches target which claims it
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)

        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)
        self.assertEquals(0, playfield.balls)


    def test_eject_successful_to_playfield(self):
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
        if balls < 0:
            raise Exception("Balls went negative")

        self._enter += balls

    def _captured_from_pf(self, balls, **kwargs):
        self._captured += balls


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
        self._enter = -1
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

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.count_balls())

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        assert not coil_diverter.disable.called

        self.assertEquals(-1, self._enter)
        self.assertEquals(-1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)


    def test_eject_to_pf_and_other_trough(self):
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

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = -1

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        self.assertEquals(2, device1.count_balls())
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # request ball
        device4.request_ball()
        self.advance_time_and_run(1)

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.count_balls())


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
        # first ball to trough. diverter should be enabled
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
        self.assertEquals(1, device4.count_balls())

        # eject of launcher should be confirmed now and the trough should eject
        coil1.pulse.assert_called_twice_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called


        self.assertEquals(-1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.count_balls())

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())

        coil1.pulse.assert_called_twice_with()
        coil2.pulse.assert_called_twice_with()
        assert not coil3.pulse.called
        assert not coil4.pulse.called

        # ball leaves launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)

        # ball passes diverter switch
        # second ball should not be diverted
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called


        # target1 receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.count_balls())

        coil1.pulse.assert_called_twice_with()
        coil2.pulse.assert_called_twice_with()
        coil3.pulse.assert_called_once_with()
        assert not coil4.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.count_balls())

        self.assertEquals(-1, self._captured)

        self.assertEquals(1, playfield.balls)
        self.assertEquals(0, self._missing)


    def test_eject_ok_to_receive(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = -1

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEquals(2, device1.count_balls())
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # request an ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # request a second ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called


        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.count_balls())


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())


        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.count_balls())

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # ball passes diverter switch
        # first ball to target1. diverter should be not enabled
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called

        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()

        # target1 receives and should eject it right away
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.count_balls())


        # eject of launcher should be confirmed now but target1 did not request
        # the next ball
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        coil3.pulse.assert_called_once_with()
        self.advance_time_and_run(1)

        self.assertEquals(-1, self._captured)

        self.assertEquals(0, playfield.balls)
        self.assertEquals(0, self._missing)


        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.count_balls())

        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        coil3.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.count_balls())

        # launcher receives a ball and should send it to target1
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())
        self.assertEquals(-1, self._captured)

        # launcher should now eject the second ball
        coil1.pulse.assert_called_twice_with()
        coil2.pulse.assert_called_twice_with()
        coil3.pulse.assert_called_once_with()

        # ball leaves launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)


        # ball passes diverter switch
        # second ball should not be diverted
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called

        # target1 receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.count_balls())

        coil1.pulse.assert_called_twice_with()
        coil2.pulse.assert_called_twice_with()
        coil3.pulse.assert_called_twice_with()

        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.count_balls())

        self.assertEquals(-1, self._captured)

        self.assertEquals(2, playfield.balls)
        self.assertEquals(0, self._missing)

        # check that timeout behave well
        self.advance_time_and_run(1000)

    def test_missing_ball_idle(self):
        coil1 = self.machine.coils['eject_coil1']
        device1 = self.machine.ball_devices['test_trough']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the balls
        coil1.pulse = MagicMock()
        self.assertEquals(2, device1.count_balls())

        # steal a ball from trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 0)
        self.advance_time_and_run(1)
        assert not coil1.pulse.called
        self.assertEquals(1, self._missing)
        self.assertEquals(0, self._captured)
        self.assertEquals(1, playfield.balls)

        # count should be on less and one ball missing
        self.assertEquals(1, device1.count_balls())

        # request an ball
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device1.count_balls())

        # ball randomly reappears
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.advance_time_and_run(1)

        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.count_balls())

        self.assertEquals(0, playfield.balls)
        self.assertEquals(1, self._missing)
        self.assertEquals(1, self._captured)


    def test_ball_entry_during_eject(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        self.assertEquals(2, device1.count_balls())
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called

        # assume there are already two balls on the playfield
        playfield.balls = 2

        # request an ball to pf
        playfield.add_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called


        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.count_balls())


        # launcher receives and ejects ball
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())

        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called

        # important: ball does not leave launcher here

        # ball passes diverter switch
        # second ball should not be diverted
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        assert not coil_diverter.enable.called

        # target1 receives and ejects
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device3.count_balls())

        coil1.pulse.assert_called_twice_with()
        coil2.pulse.assert_called_twice_with()
        coil3.pulse.assert_called_twice_with()

        # ball left target1
        self.machine.switch_controller.process_switch("s_ball_switch_target1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device3.count_balls())

        # target captured one ball because it did not leave the launcher
        self.assertEquals(1, self._captured)

        # there is no new ball on the playfield because the ball is still in the launcher
        self.assertEquals(2, playfield.balls)
        self.assertEquals(0, self._missing)

        # ball disappears from launcher
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.count_balls())

        # eject times out
        self.advance_time_and_run(15)
        # ball goes missing and magically the playfield count is right again
        self.advance_time_and_run(40)
        self.assertEquals(1, self._missing)
        self.assertEquals(3, playfield.balls)

        # check that timeout behave well
        self.advance_time_and_run(1000)

    def _block_eject(self, queue, **kwargs):
        self._queue = queue
        queue.wait()

    def test_ball_entry_during_ball_requested(self):
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()
        self.assertEquals(2, device1.count_balls())
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # request ball
        target3.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.count_balls())


        # in the meantime device4 receives a (drained) ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.count_balls())
        self.assertEquals(1, self._captured)
        self._captured = 0


        # launcher receives but cannot ejects ball yet
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())

        # target 2 ejects to target 3
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.count_balls())

        # still no eject of launcher
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        # target 3 receives
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 1)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.count_balls())

        # launcher should eject
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.count_balls())

        # ball passes diverter switch
        # first ball to trough. diverter should be enabled
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.count_balls())
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)



    def test_eject_attempt_blocking(self):
        # this test is a bit plastic. we hack get_additional_ball_capacity
        # the launcher device will try to do an eject while device4 is busy.
        # at the moment we cannot trigger this case but it may happen with
        # devices which wait before they eject
        coil1 = self.machine.coils['eject_coil1']
        coil2 = self.machine.coils['eject_coil2']
        coil3 = self.machine.coils['eject_coil3']
        coil4 = self.machine.coils['eject_coil4']
        coil5 = self.machine.coils['eject_coil5']
        coil_diverter = self.machine.coils['c_diverter']
        device1 = self.machine.ball_devices['test_trough']
        device2 = self.machine.ball_devices['test_launcher']
        device3 = self.machine.ball_devices['test_target1']
        device4 = self.machine.ball_devices['test_target2']
        target3 = self.machine.ball_devices['test_target3']
        playfield = self.machine.ball_devices['playfield']

        device4.get_additional_ball_capacity = lambda *args: 10

        self.machine.events.add_handler('balldevice_captured_from_playfield', self._captured_from_pf)
        self.machine.events.add_handler('balldevice_1_ball_missing', self._missing_ball)
        self._captured = 0
        self._missing = 0


        # add two initial balls to trough
        self.machine.switch_controller.process_switch("s_ball_switch1", 1)
        self.machine.switch_controller.process_switch("s_ball_switch2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(2, self._captured)
        self._captured = 0

        self.assertEquals(0, playfield.balls)

        # it should keep the ball
        coil1.pulse = MagicMock()
        coil2.pulse = MagicMock()
        coil3.pulse = MagicMock()
        coil4.pulse = MagicMock()
        coil5.pulse = MagicMock()
        self.assertEquals(2, device1.count_balls())
        assert not coil1.pulse.called
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        # request ball
        target3.request_ball()
        self.advance_time_and_run(1)

        # trough eject
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        assert not coil4.pulse.called
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch2", 0)
        self.advance_time_and_run(1)
        self.assertEquals(1, device1.count_balls())


        # in the meantime device4 receives a (drained) ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.count_balls())
        self.assertEquals(1, self._captured)
        self._captured = 0


        # launcher receives but cannot ejects ball yet
        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device2.count_balls())

        # however launcher will try to eject because we hacked
        # get_additional_ball_capacity. device4 should block the eject

        # target 2 ejects to target 3
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_target2_1", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.count_balls())

        # still no eject of launcher
        coil1.pulse.assert_called_once_with()
        assert not coil2.pulse.called
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        # target 3 receives
        self.machine.switch_controller.process_switch("s_ball_switch_target3", 1)
        self.advance_time_and_run(1)
        self.assertEquals(0, device4.count_balls())

        # launcher should eject
        coil1.pulse.assert_called_once_with()
        coil2.pulse.assert_called_once_with()
        assert not coil3.pulse.called
        coil4.pulse.assert_called_once_with()
        assert not coil5.pulse.called

        self.machine.switch_controller.process_switch("s_ball_switch_launcher", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, device2.count_balls())

        # ball passes diverter switch
        # first ball to trough. diverter should be enabled
        coil_diverter.enable = MagicMock()
        coil_diverter.disable = MagicMock()
        self.machine.switch_controller.process_switch("s_diverter", 1)
        self.advance_time_and_run(0.01)
        self.machine.switch_controller.process_switch("s_diverter", 0)
        self.advance_time_and_run(1)
        coil_diverter.enable.assert_called_once_with()
        assert not coil_diverter.disable.called

        # target2 receives and keeps ball
        self.machine.switch_controller.process_switch("s_ball_switch_target2_2", 1)
        self.advance_time_and_run(1)
        self.assertEquals(1, device4.count_balls())
        self.assertEquals(0, self._captured)
        self.assertEquals(0, self._missing)

