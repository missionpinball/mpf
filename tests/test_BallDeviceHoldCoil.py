import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestBallDevicesHoldCoil(MpfTestCase):

  def getConfigFile(self):
      return 'test_hold_coil.yaml'

  def getMachinePath(self):
      return '../tests/machine_files/ball_device/'

  def test_holdcoil_with_direct_release(self):
      self.machine.coils['hold_coil'].enable = MagicMock()
      self.machine.coils['hold_coil'].disable = MagicMock()
      # after hold switch was posted it should enable the hold_coil
      self.machine.events.post('test_hold_event')
      self.machine.coils['hold_coil'].enable.assert_called_once_with()
      assert not self.machine.coils['hold_coil'].disable.called

      # wait some more. coil should stay active
      self.advance_time_and_run(300)
      self.machine.coils['hold_coil'].enable.assert_called_once_with()
      assert not self.machine.coils['hold_coil'].disable.called

      # we trigger entrance switch
      self.assertEqual(0, self.machine.ball_devices['test'].balls)
      self.machine.coils['hold_coil'].enable = MagicMock()
      self.machine.coils['hold_coil'].disable = MagicMock()
      self.machine.switch_controller.process_switch(name='s_entrance',state=1);
      self.machine.switch_controller.process_switch(name='s_entrance',state=0);

      self.advance_time_and_run(300)
      self.assertEqual(0, self.machine.ball_devices['test'].balls)

      # the device should eject the ball right away because nobody claimed it
      self.machine.coils['hold_coil'].disable.assert_called_once_with()
      assert not self.machine.coils['hold_coil'].enable.called

  def test_holdcoil_which_keeps_ball(self):
      # add one ball
      self.assertEqual(0, self.machine.ball_devices['test2'].balls)
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.machine.events.post('test_hold_event2')
      self.machine.switch_controller.process_switch(name='s_entrance2',state=1);
      self.machine.switch_controller.process_switch(name='s_entrance2',state=0);

      self.advance_time_and_run(300)
      self.machine.coils['hold_coil2'].enable.assert_called_once_with()
      assert not self.machine.coils['hold_coil2'].disable.called
      self.assertEqual(1, self.machine.ball_devices['test2'].balls)

      # add a second ball
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.machine.events.post('test_hold_event2')
      self.machine.switch_controller.process_switch(name='s_entrance2',state=1);
      self.machine.switch_controller.process_switch(name='s_entrance2',state=0);
      self.advance_time_and_run(300)
      self.machine_run()
      self.machine.coils['hold_coil2'].enable.assert_called_once_with()
      assert not self.machine.coils['hold_coil2'].disable.called
      self.assertEqual(2, self.machine.ball_devices['test2'].balls)

      # eject one ball
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.machine.ball_devices['test2'].eject()
      self.advance_time_and_run(0.2)
      self.machine.coils['hold_coil2'].disable.assert_called_once_with()
      assert not self.machine.coils['hold_coil2'].enable.called

      # it should reenable the hold coil after 1s because there is a second ball
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.advance_time_and_run(2)
      assert not self.machine.coils['hold_coil2'].disable.called
      self.machine.coils['hold_coil2'].enable.assert_called_once_with()
      self.assertEqual(1, self.machine.ball_devices['test2'].balls)


  def test_holdcoil_which_keeps_ball_multiple_entries(self):
      # add one ball
      self.machine.ball_devices['test2'].balls = 1

      # eject one ball
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.machine.ball_devices['test2'].eject()
      self.advance_time_and_run(0.2)
      self.machine.coils['hold_coil2'].disable.assert_called_once_with()
      assert not self.machine.coils['hold_coil2'].enable.called

      # during the hold add another ball. it should not enable hold now
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.machine.events.post('test_hold_event2')
      self.machine.switch_controller.process_switch(name='s_entrance2',state=1);
      self.machine.switch_controller.process_switch(name='s_entrance2',state=0);
      self.advance_time_and_run(0.2)
      assert not self.machine.coils['hold_coil2'].disable.called
      assert not self.machine.coils['hold_coil2'].enable.called

      # it should reenable the hold coil after 1s because there is a second ball
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.advance_time_and_run(2)
      assert not self.machine.coils['hold_coil2'].disable.called
      self.machine.coils['hold_coil2'].enable.assert_called_once_with()
      self.assertEqual(1, self.machine.ball_devices['test2'].balls)

      # eject that ball. coil should stay off
      self.machine.coils['hold_coil2'].enable = MagicMock()
      self.machine.coils['hold_coil2'].disable = MagicMock()
      self.machine.ball_devices['test2'].eject()
      self.advance_time_and_run(300)
      self.machine.coils['hold_coil2'].disable.assert_called_once_with()
      assert not self.machine.coils['hold_coil2'].enable.called
      self.assertEqual(0, self.machine.ball_devices['test2'].balls)

