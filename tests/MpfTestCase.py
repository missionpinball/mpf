import unittest

from mpf.system.machine import MachineController
import logging
from datetime import datetime
import socket
import os
from optparse import OptionParser
import errno
import version
import sys

# TODO: mock MachineController
# TODO: mock DelayManager + Tasks
# TODO: mock BCP and prevent logs


class MpfTestCase(unittest.TestCase):

    def getOptions(self):
        return {
            'physical_hw': False,
            'mpfconfigfile': "mpf/mpfconfig.yaml",
            'machinepath': self.getMachinePath(),
            'configfile': self.getConfigFile(),
               }

    def setUp(self):
        # TODO: more unittest way of logging
    
        # define a Handler which writes messages to console
        console = logging.StreamHandler()
        console.setLevel(logging.ERROR)
        
        # set a format which is simpler for console use
        formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')
        
        # tell the handler to use this format
        console.setFormatter(formatter)
        
        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

        # init machine
        self.machine = MachineController(self.getOptions())

    def tearDown(self):
        self.machine = None

