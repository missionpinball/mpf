from mpf.tests.MpfTestCase import MpfTestCase
from mpf.platforms import fast
import time


class MockSerialCommunicator:
    expected_commands = []

    def __init__(self, machine, send_queue, receive_queue, platform, baud, port):
        # ignored variable
        del machine, send_queue, baud, port
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


class TestFast(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/fast/'

    def get_platform(self):
        return 'fast'

    def setUp(self):
        self.communicator = fast.SerialCommunicator
        fast.SerialCommunicator = MockSerialCommunicator
        fast.serial_imported = True
        MockSerialCommunicator.expected_commands = {
            "SA:": "SA:1,00,8,00000000",
            "SN:16,01,a,a": "SN:",
            "SN:07,01,a,a": "SN:",
            "SN:1A,01,a,a": "SN:",
            "DN:04,00,00,00" : False,
            "DN:06,00,00,00" : False,
            "DN:09,00,00,00" : False,
            "DN:10,00,00,00" : False,
            "DN:11,00,00,00" : False,
        }
        # FAST should never call sleep. Make it fail
        self.sleep = time.sleep
        time.sleep = None

        super().setUp()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def tearDown(self):
        super().tearDown()

        # restore modules to keep the environment clean
        time.sleep = self.sleep
        fast.SerialCommunicator = self.communicator

    def test_pulse(self):
        MockSerialCommunicator.expected_commands = {
                "DN:04,89,00,10,17,ff,00,00,00": False
        }
        # pulse coil 4
        self.machine.coils.c_test.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils.c_test.enable()

    def test_allow_enable(self):
        MockSerialCommunicator.expected_commands = {
                "DN:06,C1,00,18,17,ff,ff,00": False
        }
        self.machine.coils.c_test_allow_enable.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_hw_rule_pulse(self):
        MockSerialCommunicator.expected_commands = {
                "DN:09,01,16,10,0A,ff,00,00,00": False
        }
        self.machine.autofires.ac_slingshot_test.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        MockSerialCommunicator.expected_commands = {
                "DN:09,81": False
        }
        self.machine.autofires.ac_slingshot_test.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_hw_rule_pulse_pwm(self):
        MockSerialCommunicator.expected_commands = {
                "DN:10,89,00,10,0A,89,00,00,00": False
        }
        self.machine.coils.c_pulse_pwm_mask.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        MockSerialCommunicator.expected_commands = {
                "DN:10,C1,00,18,0A,89,AA,00": False
        }
        self.machine.coils.c_pulse_pwm_mask.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_hw_rule_pulse_pwm32(self):
        MockSerialCommunicator.expected_commands = {
                "DN:11,89,00,10,0A,89898989,00,00,00": False
        }
        self.machine.coils.c_pulse_pwm32_mask.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        MockSerialCommunicator.expected_commands = {
                "DN:11,C1,00,18,0A,89898989,AA89AA89,00": False
        }
        self.machine.coils.c_pulse_pwm32_mask.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_hw_rule_pulse_inverted_switch(self):
        MockSerialCommunicator.expected_commands = {
                "DN:09,11,1A,10,0A,ff,00,00,00": False
        }
        self.machine.autofires.ac_inverted_switch.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_servo(self):
        # go to min position
        MockSerialCommunicator.expected_commands = {
                "XO:03,00": False
        }
        self.machine.servos.servo1.go_to_position(0)
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # go to max position
        MockSerialCommunicator.expected_commands = {
                "XO:03,FF": False
        }
        self.machine.servos.servo1.go_to_position(1)
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def _switch_hit_cb(self):
        self.switch_hit = True

    def test_switch_changes(self):
        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))
        self.assertFalse(self.switch_hit)

        self.machine.events.add_handler("s_test_active", self._switch_hit_cb)
        self.machine.default_platform.net_connection.receive_queue.put("-N:07")
        self.advance_time_and_run(1)

        self.assertTrue(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))
        self.switch_hit = False

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))

        self.machine.default_platform.net_connection.receive_queue.put("/N:07")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertFalse(self.machine.switch_controller.is_active("s_test"))

    def test_switch_changes_nc(self):
        self.switch_hit = False
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))
        self.assertFalse(self.switch_hit)

        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))

        self.machine.default_platform.net_connection.receive_queue.put("-N:1A")
        self.advance_time_and_run(1)
        self.assertFalse(self.switch_hit)
        self.assertFalse(self.machine.switch_controller.is_active("s_test_nc"))

        self.machine.events.add_handler("s_test_nc_active", self._switch_hit_cb)
        self.machine.default_platform.net_connection.receive_queue.put("/N:1A")
        self.advance_time_and_run(1)

        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))
        self.assertTrue(self.switch_hit)
        self.switch_hit = False
