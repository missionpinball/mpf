import unittest

from mpf.system.machine import MachineController
from .MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestPlayfieldTransfer(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/playfield_transfer/'

    def testBallPassThrough(self):
        pf1 = self.machine.ball_devices['playfield1']
        pf2 = self.machine.ball_devices['playfield2']

        pf1.balls = 2
        pf2.balls = 2
        
        self.machine.switch_controller.process_switch("s_transfer", 1)
        self.advance_time_and_run(2)

        self.assertEqual(1, pf1.balls)
        self.assertEqual(3, pf2.balls)
