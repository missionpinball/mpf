import time

from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSerial, MockSocket


class MockPinotaurSocket(MockSocket, MockSerial):

    def read(self, length):
        del length
        if not self.queue:
            return b""
        msg = self.queue.pop()
        return msg

    def read_ready(self):
        return bool(self.queue)

    def write_ready(self):
        return True

    def write(self, msg):
        """Write message."""
        # print("Serial received: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
        total_msg_len = len(msg)
        while msg:
            if len(msg) < 3:
                raise AssertionError("Msg needs to be at least 3 chars.")
            command = msg[0]
            if msg[0] != ord(b'<'):
                raise AssertionError("Msg should start with <. Msg: {}".format("".join("\\x%02x" % b for b in msg)))
            cmd = msg[1]
            payload_length = (msg[2] ^ 0x81) >> 1

            if len(msg) < 3 + payload_length:
                raise AssertionError("Msg is too short. Length: {} Payload length: {} Msg: {}",
                                     len(msg), payload_length, "".join("\\x%02x" % b for b in msg))

            self._handle_msg(msg[0:3 + payload_length])
            msg = msg[3 + payload_length:]

        return total_msg_len

    def _handle_msg(self, msg):
        if msg in self.permanent_commands and msg not in self.expected_commands:
            if self.permanent_commands[msg] is not None:
                self.queue.append(self.permanent_commands[msg])
            return len(msg)

        if msg not in self.expected_commands:
            self.crashed = True
            print("Unexpected command: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
            raise AssertionError("Unexpected command: " + "".join("\\x%02x" % b for b in msg) +
                                 " len: " + str(len(msg)))

        if self.expected_commands[msg] is not None:
            self.queue.append(self.expected_commands[msg])

        del self.expected_commands[msg]
        return len(msg)

    def send(self, data):
        return self.write(data)

    def recv(self, size):
        return self.read(size)

    def __init__(self, api_version):
        super().__init__()
        self.name = "SerialMock"
        self.expected_commands = {}
        self.queue = []
        self.permanent_commands = {}
        self.crashed = False
        self.api_version = api_version


class TestPinotaur(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/pinotaur/'

    def _mock_loop(self):
        self.clock.mock_serial("com1", self.serialMock)

    def tearDown(self):
        self.assertFalse(self.serialMock.crashed)
        super().tearDown()

    def get_platform(self):
        return False

    def _wait_for_processing(self):
        start = time.time()
        while self.serialMock.expected_commands and not self.serialMock.crashed and time.time() < start + 1:
            self.advance_time_and_run(.01)

    def setUp(self):
        self.expected_duration = 1.5
        self.serialMock = MockPinotaurSocket(api_version=8)

        self.serialMock.permanent_commands = {
            b'<\x59\x81': b'>\x59\x7f',   # changed switches? -> no
            b'<\x65\x81': b'>\x65\x00'    # watchdog
        }

        self.serialMock.expected_commands = {
            b'<\x64\x81': b'>\x64\x00',             # reset
            b'<\x00\x81': b'>\x00Pinotaur\00',      # hw
            b'<\x01\x81': b'>\x014.01\00',          # version
            # b'<\x02\x81': b'>\x020.08\00',        # api version
            b'<\x03\x81': b'>\x03\x28',             # get number of lamps -> 40
            b'<\x04\x81': b'>\x04\x09',             # get number of solenoids -> 9
            b'<\x09\x81': b'>\x09\x58',             # get number of switches -> 88
            b'<\x5f\x81': False,                    # flush changes
            b'<\x60\x83\x01': b'>\x60\x00',         # enable relay
            b'<\x19\x85\x00\x0a': b'>\x19\x00',     # set recycle time
            b'<\x19\x85\x01\x0a': b'>\x19\x00',     # set recycle time
            b'<\x19\x85\x02\xff': b'>\x19\x00',     # set recycle time
            b'<\x19\x85\x05\x1e': b'>\x19\x00',     # set recycle time
            b'<\x19\x85\x06\x0a': b'>\x19\x00',     # set recycle time
            b'<\x19\x85\x07\x0a': b'>\x19\x00',     # set recycle time
        }

        for number in range(128):
            if number == 4:
                self.serialMock.expected_commands[bytes([ord(b'<'), 0x58, 0x83, number])] = b'>\x58\x00\x01'
            else:
                self.serialMock.expected_commands[bytes([ord(b'<'), 0x58, 0x83, number])] = b'>\x58\x00\x00'

        super().setUp()

        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def test_platform(self):
        self.maxDiff = None
        infos = """Pinotaur connected via serial on com1
Hardware: Pinotaur Firmware Version: 4
Input map: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '96', '97', '98', '99', '100', '101', '102', '103', '104', '105', '106', '107', '108', '109', '110', '111', '112', '113', '114', '115', '116', '117', '118', '119', '120', '121', '122', '123', '124', '125', '126', '127']
Coil count: 9
Modern lights count: 88
Traditional lights count: 40
"""

        self.assertEqual(self.machine.default_platform.get_info_string(), infos)

        # wait for watchdog
        self.serialMock.expected_commands = {
            b'<\x65\x81': b'>\x65\x00'    # watchdog
        }
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test initial switch state
        self.assertSwitchState("s_test00", False)
        self.assertSwitchState("s_test4", True)
        self.assertSwitchState("s_test60_nc", True)

        self.serialMock.expected_commands = {
            b'<\x59\x81': b'>\x59\x04',   # changed switches? -> 4 to off
        }
        self.advance_time_and_run(.1)
        # turns inactive
        self.assertSwitchState("s_test4", False)

        self.serialMock.expected_commands = {
            b'<\x59\x81': b'>\x59\x84',   # changed switches? -> 4 to on
        }
        self.advance_time_and_run(.1)
        # turns active
        self.assertSwitchState("s_test4", True)

        self.serialMock.expected_commands = {
            b'<\x59\x81': b'>\x59\xBC',   # changed switches? -> 60 to on
        }
        self.advance_time_and_run(.1)
        # turns inactive (because of NC)
        self.assertSwitchState("s_test60_nc", False)
        self.assertFalse(self.serialMock.expected_commands)

        # pulse coil
        self.serialMock.expected_commands = {
            b'<\x12\x87\x00\x01\x01': b'>\x12\x00',     # set pulse_pwm to full on
            b'<\x17\x85\x00\x0a': b'>\x17\x00'          # pulse for 10ms
        }
        self.machine.coils["c_test"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse trough eject. enable and disable in software
        self.serialMock.expected_commands = {
            b'<\x12\x87\x02\x01\x01': b'>\x12\x00',     # set pulse_pwm to full on
            b'<\x11\x87\x02\xff\xff': b'>\x11\x00',     # hold time = inf
            b'<\x13\x8f\x02\x01\x01\x00\x00\x00\x00': b'>\x13\x00',  # set hold pwm
            b'<\x17\x85\x02\x01': b'>\x17\x00'       # enable (looks like a pulse but this is actually enable)
        }
        self.machine.coils["c_test_long_pulse"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.advance_time_and_run(1.5)
        self.serialMock.expected_commands = {
            b'<\x16\x83\x02': b'>\x16\x00'       # disable
        }
        self.advance_time_and_run()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # enable coil
        self.serialMock.expected_commands = {
            b'<\x12\x87\x01\x01\x01': b'>\x12\x00',     # set pulse_pwm to full on
            b'<\x11\x87\x01\xff\xff': b'>\x11\x00',     # hold time = inf
            b'<\x13\x8f\x01\x01\x01\x00\x00\x00\x00': b'>\x13\x00',  # set hold pwm
            b'<\x17\x85\x01\x0a': b'>\x17\x00'       # enable (looks like a pulse but this is actually enable)
        }
        self.machine.coils["c_test_allow_enable"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # disable coil
        self.serialMock.expected_commands = {
            b'<\x16\x83\x01': b'>\x16\x00'       # disable
        }
        self.machine.coils["c_test_allow_enable"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # TODO: implement lights
        # # test light enable (using light 3)
        # self.serialMock.expected_commands = {
        #     b'\x0b\x03': None
        # }
        # self.machine.lights["test_light0"].on(key="test")
        # self._wait_for_processing()
        # self.assertFalse(self.serialMock.expected_commands)
        #
        # # disable light (using light 3)
        # self.serialMock.expected_commands = {
        #     b'\x0c\x03': None
        # }
        # self.machine.lights["test_light0"].remove_from_stack_by_key("test")
        # self._wait_for_processing()
        # self.assertFalse(self.serialMock.expected_commands)

    def test_rules(self):
        """Test HW Rules."""
        self.skipTest("Not implemented yet.")
        return
        # wait for watchdog
        self.serialMock.expected_commands = {
            b'\x65': b'\x00'  # watchdog
        }
        self._wait_for_processing()

        self.serialMock.expected_commands = {
            b'<\x3c>\x05\x01\x02\x00\x1e\xff\x00\x03\x02\x00': None,      # create rule for main
            b'<\x06\x01\x00\x00\x0a\xff\xff\x03\x00\x00': None,      # create rule for hold
        }
        self.machine.flippers["f_test_hold_eos"].enable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'<\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for main
            b'<\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for hold
        }
        self.machine.flippers["f_test_hold_eos"].disable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x3c\x07\x03\x00\x00\x0a\xff\x00\x01\x00\x00': None,      # add rule for slingshot
            b'\x19\x07\x14': None
        }
        self.machine.autofire_coils["ac_slingshot"].enable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x3c\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for slingshot
        }
        self.machine.autofire_coils["ac_slingshot"].disable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test recycle
        # pulse coil
        self.serialMock.expected_commands = {
            b'\x18\x00\x0a': None,      # set pulse_ms to 10ms
            b'\x17\x00': None
        }
        self.machine.coils["c_test"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def test_lights(self):
        """Test lights."""
        self.skipTest("Not implemented yet.")
        return
        # set color to one light without fade
        self.serialMock.expected_commands = {
            b'\x0d\x00\x00\x00\x00\x03\x11\x22\x33': None,      # fade with 0ms fade time
        }
        self.machine.lights["test_light0"].color([0x11, 0x22, 0x33], key="test")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set color again (should do nothing)
        self.machine.lights["test_light0"].remove_from_stack_by_key("test")
        self.machine.lights["test_light0"].color([0x11, 0x22, 0x33], fade_ms=100)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set color to the second light without fade
        self.serialMock.expected_commands = {
            b'\x0d\x00\x03\x00\x00\x04\x11\x22\x33\x11': None,      # fade with 0ms fade time starting at channel 3
                                                                    # 4 channels because this is a RGBW light
        }
        self.machine.lights["test_light1"].color([0x11, 0x22, 0x33])
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # fade both lights together (fade depending on serial timing)
        self.serialMock.expected_commands = {
            b'\x0d\x00\x00\x01\x18\x07\xaa\xbb\xcc\xdd\xee\xff\xdd': None,      # fade with 300ms fade time
            b'\x0d\x00\x00\x01\x19\x07\xaa\xbb\xcc\xdd\xee\xff\xdd': None,      # fade with 300ms fade time
            b'\x0d\x00\x00\x01\x20\x07\xaa\xbb\xcc\xdd\xee\xff\xdd': None,      # fade with 300ms fade time
            b'\x0d\x00\x00\x01\x21\x07\xaa\xbb\xcc\xdd\xee\xff\xdd': None,      # fade with 300ms fade time
            b'\x0d\x00\x00\x01\x22\x07\xaa\xbb\xcc\xdd\xee\xff\xdd': None,      # fade with 300ms fade time
        }
        self.machine.lights["test_light0"].color([0xaa, 0xbb, 0xcc], fade_ms=300)
        self.machine.lights["test_light1"].color([0xdd, 0xee, 0xff], fade_ms=300)
        start = time.time()
        while len(self.serialMock.expected_commands) > 4 and not self.serialMock.crashed and time.time() < start + 10:
            self.advance_time_and_run(.01)
        self.assertEqual(4, len(self.serialMock.expected_commands))
