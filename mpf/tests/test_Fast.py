from mpf.tests.MpfTestCase import MpfTestCase
from mpf.platforms import fast
import time


class MockSerialCommunicator:
    expected_commands = []

    def __init__(self, machine, send_queue, receive_queue, platform, baud,
                 port):
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
                self.receive_queue.put(
                    MockSerialCommunicator.expected_commands[cmd])
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
            "SN:01,01,a,a": "SN:",
            "SN:02,01,a,a": "SN:",
            "SN:16,01,a,a": "SN:",
            "SN:07,01,a,a": "SN:",
            "SN:1A,01,a,a": "SN:",
            "DN:04,00,00,00": False,
            "DN:06,00,00,00": False,
            "DN:09,00,00,00": False,
            "DN:10,00,00,00": False,
            "DN:11,00,00,00": False,
            "DN:12,00,00,00": False,
            "DN:20,00,00,00": False,
            "DN:21,00,00,00": False,
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

    def test_long_pulse(self):
        # enable command
        MockSerialCommunicator.expected_commands = {
            "DN:12,C1,00,18,00,ff,ff,00": False
        }
        self.machine.coils.c_long_pulse.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # disable command
        MockSerialCommunicator.expected_commands = {
            "TN:12,02": False
        }

        self.advance_time_and_run(1)
        # pulse_ms is 2000ms, so after 1s, this should not be sent
        self.assertTrue(MockSerialCommunicator.expected_commands)

        self.advance_time_and_run(1)
        # but after 2s, it should be
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_enable_exception(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.coils.c_test.enable()

    def test_enable_exception_hw_rule(self):
        # enable coil which does not have allow_enable
        with self.assertRaises(AssertionError):
            self.machine.default_platform.set_pulse_on_hit_and_enable_and_release_rule(
                self.machine.switches.s_test,
                self.machine.coils.c_test)

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

    def test_flipper_single_coil(self):
        # manual flip no hw rule
        MockSerialCommunicator.expected_commands = {
            "DN:20,89,00,10,0A,ff,00,00,00": False
        }
        self.machine.coils.c_flipper_main.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # manual enable no hw rule
        MockSerialCommunicator.expected_commands = {
            "DN:20,C1,00,18,0A,ff,01,00": False
        }
        self.machine.coils.c_flipper_main.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # manual disable no hw rule
        MockSerialCommunicator.expected_commands = {
            "TN:20,02": False
        }
        self.machine.coils.c_flipper_main.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # enable
        MockSerialCommunicator.expected_commands = {
            "DN:20,01,01,18,0B,ff,01,00,00": False
        }
        self.machine.flippers.f_test_single.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # manual flip with hw rule in action
        MockSerialCommunicator.expected_commands = {
            "TN:20,01": False,  # pulse
            "TN:20,00": False   # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # manual enable with hw rule
        MockSerialCommunicator.expected_commands = {
            "TN:20,03": False
        }
        self.machine.coils.c_flipper_main.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # manual disable with hw rule
        MockSerialCommunicator.expected_commands = {
            "TN:20,02": False,
            "TN:20,00": False   # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        # disable
        MockSerialCommunicator.expected_commands = {
            "DN:20,81": False
        }
        self.machine.flippers.f_test_single.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        MockSerialCommunicator.expected_commands = {
            "DN:20,01,01,10,0A,ff,00,00,00": False,
            "DN:21,01,01,18,0A,ff,01,00,00": False,
        }
        self.machine.flippers.f_test_hold.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

        MockSerialCommunicator.expected_commands = {
            "DN:20,81": False,
            "DN:21,81": False
        }
        self.machine.flippers.f_test_hold.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands)

    def test_flipper_two_coils_with_eos(self):
        # Currently broken in the FAST platform
        return
        # self.machine.flippers.f_test_hold_eos.enable()
