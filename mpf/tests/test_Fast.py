from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.platforms import fast
import time


class MockSerialCommunicator:
    expected_commands = {}
    leds = {}

    def __init__(self, machine, send_queue, receive_queue, platform, baud,
                 port):
        # ignored variable
        del machine, send_queue, baud
        self.platform = platform
        self.receive_queue = receive_queue
        if port == "com4":
            self.type = 'NET'
            self.platform.register_processor_connection("NET", self)
        elif port == "com5":
            self.type = 'DMD'
            self.platform.register_processor_connection("DMD", self)
        elif port == "com6":
            self.type = 'RGB'
            self.platform.register_processor_connection("RGB", self)
        else:
            raise AssertionError("invalid port for test")

    def send(self, cmd):
        cmd = str(cmd)

        if cmd[:3] == "WD:":
            return

        if self.type == "RGB" and cmd[:3] == "RS:":
            MockSerialCommunicator.leds[cmd[3:5]] = cmd[5:]
            return

        if cmd in MockSerialCommunicator.expected_commands[self.type]:
            if MockSerialCommunicator.expected_commands[self.type][cmd]:
                self.receive_queue.put(
                    MockSerialCommunicator.expected_commands[self.type][cmd])
            del MockSerialCommunicator.expected_commands[self.type][cmd]
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
        MockSerialCommunicator.expected_commands['DMD'] = {}
        MockSerialCommunicator.expected_commands['RGB'] = {
            "RF:0": False,
            "RA:000000": False,
            "RF:00": False,
        }
        MockSerialCommunicator.expected_commands['NET'] = {
            "SA:": "SA:1,00,8,00000000",
            "SN:01,01,0A,0A": "SN:",
            "SN:02,01,0A,0A": "SN:",
            "SN:16,01,0A,0A": "SN:",
            "SN:07,01,0A,0A": "SN:",
            "SN:1A,01,0A,0A": "SN:",
            "DN:04,00,00,00": False,
            "DN:06,00,00,00": False,
            "DN:09,00,00,00": False,
            "DN:10,00,00,00": False,
            "DN:11,00,00,00": False,
            "DN:12,00,00,00": False,
            "DN:20,00,00,00": False,
            "DN:21,00,00,00": False,
            "GI:2A,FF": False,
        }
        # FAST should never call sleep. Make it fail
        self.sleep = time.sleep
        time.sleep = None

        super().setUp()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def tearDown(self):
        super().tearDown()

        # restore modules to keep the environment clean
        time.sleep = self.sleep
        fast.SerialCommunicator = self.communicator

    def test_pulse(self):
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:04,89,00,10,17,ff,00,00,00": False
        }
        # pulse coil 4
        self.machine.coils.c_test.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_long_pulse(self):
        # enable command
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:12,C1,00,18,00,ff,ff,00": False
        }
        self.machine.coils.c_long_pulse.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # disable command
        MockSerialCommunicator.expected_commands['NET'] = {
            "TN:12,02": False
        }

        self.advance_time_and_run(1)
        # pulse_ms is 2000ms, so after 1s, this should not be sent
        self.assertTrue(MockSerialCommunicator.expected_commands['NET'])

        self.advance_time_and_run(1)
        # but after 2s, it should be
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

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
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:06,C1,00,18,17,ff,ff,00": False
        }
        self.machine.coils.c_test_allow_enable.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_hw_rule_pulse(self):
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:09,01,16,10,0A,ff,00,00,14": False,  # hw rule
            "SN:16,01,02,02": False                  # debounce quick on switch
        }
        self.machine.autofires.ac_slingshot_test.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:09,81": False
        }
        self.machine.autofires.ac_slingshot_test.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_hw_rule_pulse_pwm(self):
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:10,89,00,10,0A,89,00,00,00": False
        }
        self.machine.coils.c_pulse_pwm_mask.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:10,C1,00,18,0A,89,AA,00": False
        }
        self.machine.coils.c_pulse_pwm_mask.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_hw_rule_pulse_pwm32(self):
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:11,89,00,10,0A,89898989,00,00,00": False
        }
        self.machine.coils.c_pulse_pwm32_mask.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:11,C1,00,18,0A,89898989,AA89AA89,00": False
        }
        self.machine.coils.c_pulse_pwm32_mask.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_hw_rule_pulse_inverted_switch(self):
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:09,11,1A,10,0A,ff,00,00,14": False,
            "SN:1A,01,02,02": False
        }
        self.machine.autofires.ac_inverted_switch.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_servo(self):
        # go to min position
        MockSerialCommunicator.expected_commands['NET'] = {
                "XO:03,00": False
        }
        self.machine.servos.servo1.go_to_position(0)
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # go to max position
        MockSerialCommunicator.expected_commands['NET'] = {
                "XO:03,FF": False
        }
        self.machine.servos.servo1.go_to_position(1)
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

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
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:20,89,00,10,0A,ff,00,00,00": False
        }
        self.machine.coils.c_flipper_main.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # manual enable no hw rule
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:20,C1,00,18,0A,ff,01,00": False
        }
        self.machine.coils.c_flipper_main.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # manual disable no hw rule
        MockSerialCommunicator.expected_commands['NET'] = {
            "TN:20,02": False
        }
        self.machine.coils.c_flipper_main.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # enable
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:20,01,01,18,0B,ff,01,00,00": False,
            "SN:01,01,02,02": False
        }
        self.machine.flippers.f_test_single.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # manual flip with hw rule in action
        MockSerialCommunicator.expected_commands['NET'] = {
            "TN:20,01": False,  # pulse
            "TN:20,00": False   # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.pulse()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # manual enable with hw rule
        MockSerialCommunicator.expected_commands['NET'] = {
            "TN:20,03": False
        }
        self.machine.coils.c_flipper_main.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # manual disable with hw rule
        MockSerialCommunicator.expected_commands['NET'] = {
            "TN:20,02": False,
            "TN:20,00": False   # reenable autofire rule
        }
        self.machine.coils.c_flipper_main.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # disable
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:20,81": False
        }
        self.machine.flippers.f_test_single.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_flipper_two_coils(self):
        # we pulse the main coil (20)
        # hold coil (21) is pulsed + enabled
        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:20,01,01,18,0A,ff,00,00,00": False,
            "DN:21,01,01,18,0A,ff,01,00,00": False,
            "SN:01,01,02,02": False,
        }
        self.machine.flippers.f_test_hold.enable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        MockSerialCommunicator.expected_commands['NET'] = {
            "DN:20,81": False,
            "DN:21,81": False
        }
        self.machine.flippers.f_test_hold.disable()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_flipper_two_coils_with_eos(self):
        # Currently broken in the FAST platform
        return
        # self.machine.flippers.f_test_hold_eos.enable()

    def test_dmd_update(self):

        # test configure
        self.machine.default_platform.configure_dmd()

        # test set frame to buffer
        frame = bytearray()
        for i in range(4096):
            frame.append(i % 256)

        frame = bytes(frame)

        # test draw
        MockSerialCommunicator.expected_commands['DMD'] = {
            frame: False
        }

        # todo I don't know why this fails? They look the same to me?

        # self.machine.bcp.physical_dmd_update_callback(frame)
        #
        # self.advance_time_and_run(0.04)
        #
        # self.assertFalse(MockSerialCommunicator.expected_commands['DMD'])

        # TODO: test broken frames (see P-ROC test)

    def test_matrix_light(self):
        # test enable of matrix light
        MockSerialCommunicator.expected_commands['NET'] = {
            "L1:23,FF": False,
        }
        self.machine.lights.test_pdb_light.on()
        self.machine_run()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # test disable of matrix light
        MockSerialCommunicator.expected_commands['NET'] = {
            "L1:23,00": False,
        }
        self.machine.lights.test_pdb_light.off()
        self.machine_run()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_pdb_gi_light(self):
        # test gi on
        device = self.machine.gis.test_gi
        MockSerialCommunicator.expected_commands['NET'] = {
            "GI:2A,FF": False,
        }
        device.enable()
        self.machine_run()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        MockSerialCommunicator.expected_commands['NET'] = {
            "GI:2A,80": False,
        }
        device.enable(brightness=128)
        self.machine_run()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        MockSerialCommunicator.expected_commands['NET'] = {
            "GI:2A,F5": False,
        }
        device.enable(brightness=245)
        self.machine_run()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

        # test gi off
        MockSerialCommunicator.expected_commands['NET'] = {
            "GI:2A,00": False,
        }
        device.disable()
        self.machine_run()
        self.assertFalse(MockSerialCommunicator.expected_commands['NET'])

    def test_rdb_led(self):
        device = self.machine.leds.test_led
        self.assertEqual("000000", MockSerialCommunicator.leds['97'])
        MockSerialCommunicator.leds = {}
        # test led on
        device.on()
        self.advance_time_and_run(1)
        self.assertEqual("ffffff", MockSerialCommunicator.leds['97'])

        # test led off
        device.off()
        self.advance_time_and_run(1)
        self.assertEqual("000000", MockSerialCommunicator.leds['97'])

        # test led color
        device.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertEqual("02172a", MockSerialCommunicator.leds['97'])
