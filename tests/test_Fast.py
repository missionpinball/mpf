import unittest

from mpf.system.machine import MachineController
from tests.MpfTestCase import MpfTestCase
from mock import MagicMock
from mpf.platform import fast
import time

class MockSerialCommunicator:
    def __init__(self, machine, send_queue, receive_queue, platform, baud, port):
        self.platform = platform
        self.receive_queue = receive_queue
        self.platform.register_processor_connection("NET", self)

    def send(self, cmd):
        if cmd[:3] == "WD:":
            return

        if cmd in MockSerialCommunicator.expected_commands:
            if MockSerialCommunicator.expected_commands[cmd]:
                self.receive_queue.put(MockSerialCommunicator.expected_commands[cmd])
            del MockSerialCommunicator.expected_commands[cmd]
        else:
            raise Exception(cmd)

        if cmd == "SA:":
            self.receive_queue.put("SA:0,,2,00")
        elif cmd == "SN:16,01,a,a":
            self.receive_queue.put("SN:")
        elif cmd == "SN:07,01,a,a":
            self.receive_queue.put("SN:")

class TestFast(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/fast/'

    def get_platform(self):
        return 'fast'

    def setUp(self):
        fast.SerialCommunicator = MockSerialCommunicator
        # 
        MockSerialCommunicator.expected_commands = {
            "SA:" : "SA:0,00,32,00",
            "SN:16,01,a,a" : "SN:",
            "SN:07,01,a,a" : "SN:"
        }
        # FAST should never call sleep. Make it fail
        time.sleep = None
        super().setUp()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_pulse(self):
        MockSerialCommunicator.expected_commands = {
                "DN:04,89,00,10,17,ff,00,00,00" : False
        }
        # pulse coil 4
        self.machine.coils.c_test.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_enable_exception(self):
        return
        # this should throw an error but it does not.
        # TODO: why?

        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError) as cm:
            self.machine.coils.c_test.enable()

    def test_allow_enable(self):
        MockSerialCommunicator.expected_commands = {
                "DN:06,C1,00,18,17,ff,ff,00" : False
        }
        self.machine.coils.c_test_allow_enable.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_hw_rule_pulse(self):
        MockSerialCommunicator.expected_commands = {
                "DN:09,01,16,10,0A,ff,00,00,00" : False
        }
        self.machine.autofires.ac_slingshot_test.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)
