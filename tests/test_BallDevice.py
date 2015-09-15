import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock

class TestBallDevices(MpfTestCase):

  def getConfigFile(self):
      return 'test_hold_coil.yaml'

  def getMachinePath(self):
      return '../tests/machine_files/ball_device/'


  def test_holdcoil(self):
      self.machine.coils['hold_coil'].enable = MagicMock()
      self.machine.events.post('test_hold_event')
      self.machine.coils['hold_coil'].enable.assert_called_once_with()


