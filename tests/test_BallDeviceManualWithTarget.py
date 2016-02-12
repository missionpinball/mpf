import unittest

from mpf.core.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
import time
import tests.test_BallDeviceManualWithCount

class TestBallDeviceManualWithTarget(tests.test_BallDeviceManualWithCount.TestBallDeviceManualWithCount):

    def getConfigFile(self):
        return 'test_ball_device_manual_with_target.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

