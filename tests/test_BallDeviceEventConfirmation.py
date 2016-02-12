import unittest

from mpf.core.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time
import tests.test_BallDeviceSwitchConfirmation

class TestBallDeviceEventConfirmation(tests.test_BallDeviceSwitchConfirmation.TestBallDeviceSwitchConfirmation):

    def getConfigFile(self):
        return 'test_ball_device_event_confirmation.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def _hit_confirm(self):
        self.machine.events.post("launcher_confirm")

