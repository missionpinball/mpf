import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time
import tests.test_BallDeviceManualWithCount

class TestBallDeviceManualEject(tests.test_BallDeviceManualWithCount.TestBallDeviceManualWithCount):

    def getConfigFile(self):
        return 'test_ball_device_manual_eject.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_device/'

