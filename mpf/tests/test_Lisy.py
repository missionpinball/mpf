import time

from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
from mpf.platforms.lisy import lisy

from mpf.tests.MpfTestCase import MpfTestCase, test_config, MagicMock
from mpf.tests.loop import MockSerial, MockSocket

COMMAND_LENGTH = {
    0: 1,
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    6: 1,
    7: 2,
    9: 1,
    11: 2,
    12: 2,
    19: 1,
    21: 2,
    22: 2,
    23: 2,
    24: 3,
    25: 3,
    40: 2,
    41: 1,
    51: 1,
    60: 11,
    100: 1,
    101: 1,
}


class MockLisySocket(MockSocket, MockSerial):

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
            command = msg[0]
            if command == 13:
                command_length = 6 + msg[5]
            elif 30 <= command <= 35:
                if self.api_version >= 9:
                    command_length = 2 + msg[1]
                else:
                    command_length = msg.index(b'\x00') + 1
            elif command in (50, 54):
                command_length = 3 if self.api_version >= 9 else 2
            elif command == 51:
                command_length = 2 if self.api_version >= 9 else 1
            elif command in (52, 53):
                command_length = msg[3:].index(b'\x00') + 4
            else:
                command_length = COMMAND_LENGTH.get(command, None)
            if command_length is None:
                raise AssertionError("Unknown command {} in {}".format(command, "".join("\\x%02x" % b for b in msg)))
            if len(msg) < command_length:
                raise AssertionError("Message too short ({}) for command {} with length {} in {}".format(
                    len(msg), command_length, command,
                    "".join("\\x%02x" % b for b in msg)))

            self._handle_msg(msg[0:command_length])
            msg = msg[command_length:]

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


class TestLisy(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/lisy/'

    def _mock_loop(self):
        self.clock.mock_socket("localhost", 1234, self.serialMock)

    def tearDown(self):
        self.assertFalse(self.serialMock.crashed)
        super().tearDown()

    def get_platform(self):
        return False

    def _wait_for_processing(self):
        start = time.time()
        while self.serialMock.expected_commands and not self.serialMock.crashed and time.time() < start + 10:
            self.advance_time_and_run(.01)

    def setUp(self):
        self.expected_duration = 1.5
        self.serialMock = MockLisySocket(api_version=8)

        self.serialMock.permanent_commands = {
            b'\x29': b'\x7F',           # changed switches? -> no
            b'\x65': b'\x00'            # watchdog
        }

        self.serialMock.expected_commands = {
            b'\x00': b'LISY1\00',       # hw LISY1
            b'\x01': b'4.01\00',        # lisy version
            b'\x02': b'0.08\00',        # api version
            b'\x64': b'\x00',           # reset -> ok
            b'\x03': b'\x28',           # get number of lamps -> 40
            b'\x04': b'\x09',           # get number of solenoids -> 9
            b'\x06': b'\x05',           # get number of displays -> 5
            b'\x09': b'\x58',           # get number of switches -> 88
            b'\x1e\x20\x20\x20\x20\x20\x20\x20\x00': None,          # clear display
            b'\x1f\x20\x20\x20\x20\x20\x20\x20\x00': None,          # clear display
            b'\x20\x20\x20\x20\x20\x20\x20\x20\x00': None,          # clear display
        }

        for number in range(88):
            if number % 10 >= 8:
                self.serialMock.expected_commands[bytes([40, number])] = b'\x02'
            else:
                self.serialMock.expected_commands[bytes([40, number])] = b'\x00' if number != 37 else b'\x01'

        super().setUp()

        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def test_platform(self):
        self.maxDiff = None
        infos = """LISY connected via network at localhost:1234
Hardware: LISY1 Lisy Version: 4.01 API Version: 0.8
Input count: 88 Input map: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83', '84', '85', '86', '87']
Coil count: 9
Modern lights count: 0
Traditional lights count: 40
Display count: 5
"""

        self.assertEqual(self.machine.default_platform.get_info_string(), infos)

        # wait for watchdog
        self.serialMock.expected_commands = {
            b'\x65': b'\x00'            # watchdog
        }
        self._wait_for_processing()

        # test initial switch state
        self.assertSwitchState("s_test00", False)
        self.assertSwitchState("s_test37", True)
        self.assertSwitchState("s_test77_nc", True)

        self.serialMock.expected_commands = {
            b'\x29': b'\x25'        # 37 turned inactive
        }
        self.advance_time_and_run(.1)
        # turns inactive
        self.assertSwitchState("s_test37", False)

        self.serialMock.expected_commands = {
            b'\x29': b'\xA5'        # 37 turned active (again)
        }
        self.advance_time_and_run(.1)
        # turns active
        self.assertSwitchState("s_test37", True)

        self.serialMock.expected_commands = {
            b'\x29': b'\xCD'        # 77 turned active
        }
        self.advance_time_and_run(.1)
        # turns inactive (because of NC)
        self.assertSwitchState("s_test77_nc", False)

        # pulse coil
        self.serialMock.expected_commands = {
            b'\x18\x00\x0a': None,      # set pulse_ms to 10ms
            b'\x17\x00': None
        }
        self.machine.coils["c_test"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse trough eject. enable and disable in software
        self.serialMock.expected_commands = {
            b'\x18\x67\x00': None,  # set pulse_ms to 10ms
            b'\x15\x67': None       # enable
        }
        self.machine.coils["c_trough_eject"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.advance_time_and_run(2)
        self.serialMock.expected_commands = {
            b'\x16\x67': None       # disable
        }
        self.advance_time_and_run()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # enable coil
        self.serialMock.expected_commands = {
            b'\x18\x01\x0a': None,  # set pulse_ms to 10ms
            b'\x15\x01': None
        }
        self.machine.coils["c_test_allow_enable"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # disable coil
        self.serialMock.expected_commands = {
            b'\x16\x01': None
        }
        self.machine.coils["c_test_allow_enable"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test light enable (using light 3)
        self.serialMock.expected_commands = {
            b'\x0b\x03': None
        }
        self.machine.lights["test_light"].on(key="test")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # disable light (using light 3)
        self.serialMock.expected_commands = {
            b'\x0c\x03': None
        }
        self.machine.lights["test_light"].remove_from_stack_by_key("test")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # start ball. enable flipper (using light 1)
        self.serialMock.expected_commands = {
            b'\x0b\x01': None
        }
        self.post_event("ball_started")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.advance_time_and_run()

        # end ball. disable flipper (using light 1)
        self.serialMock.expected_commands = {
            b'\x0c\x01': None
        }
        self.post_event("ball_will_end")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set info display to TEST
        self.serialMock.expected_commands = {
            b'\x1E   TEST\x00': None
        }
        self.machine.segment_displays["info_display"].add_text("TEST")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set player 1 display to 42000
        self.serialMock.expected_commands = {
            b'\x1F  42000\x00': None
        }
        self.machine.segment_displays["player1_display"].add_text("42000")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set player 1 display to flashing
        self.machine.segment_displays["player1_display"].set_flashing(FlashingType.FLASH_ALL)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x1F  42000\x00': None,
            b'\x1F       \x00': None
        }

        self.advance_time_and_run(1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x1F       \x00': None
        }

        self.advance_time_and_run(.5)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x1F  42000\x00': None,
        }
        self.machine.segment_displays["player1_display"].set_flashing(FlashingType.NO_FLASH)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test sound
        self.serialMock.expected_commands = {
            b'\x32\x02': None
        }
        self.post_event("test2")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test sound file
        self.serialMock.expected_commands = {
            b'\x34\x00some_file\x00': None
        }
        self.post_event("play_file")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test sound file looping
        self.serialMock.expected_commands = {
            b'\x34\x01some_file\x00': None
        }
        self.post_event("play_file_loop")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # text to speech
        self.serialMock.expected_commands = {
            b'\x35\x02Hello MPF\x00': None
        }
        self.post_event("play_text")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set volume to 50 (32 hex)
        self.serialMock.expected_commands = {
            b'\x36\x32': None
        }
        self.post_event("volume_05")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # increase volume by 0.1 -> 60 -> hex 3C
        self.serialMock.expected_commands = {
            b'\x36\x3C': None
        }
        self.post_event("increase_volume")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # decrease volume by 0.01 -> 59 -> hex 3B
        self.serialMock.expected_commands = {
            b'\x36\x3B': None
        }
        self.post_event("decrease_volume")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test another sound
        self.serialMock.expected_commands = {
            b'\x32\x03': None
        }
        self.post_event("test3")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # stop sound
        self.serialMock.expected_commands = {
            b'\x33': None
        }
        self.post_event("test_stop")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    @test_config("config_system11.yaml")
    def test_system11(self):
        # test normal coil
        self.serialMock.expected_commands = {
            b'\x18\x00\x14': None,  # set pulse_ms to 20ms
            b'\x17\x00': None       # pulse coil 0
        }
        self.machine.coils["c_test"].pulse(20)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test C-side coil
        self.serialMock.expected_commands = {
            b'\x18\x08\x0a': None,  # set pulse_ms to 10ms to A/C relay
            b'\x15\x08': None,      # enable A/C relay
            b'\x18\x01\x14': None,  # set pulse_ms to 20ms
            b'\x17\x01': None       # pulse coil 1
        }
        self.machine.coils["c_test1_c_side"].pulse(20)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # wait for A/C disable
        self.serialMock.expected_commands = {
            b'\x16\x08': None,      # disable A/C relay
        }
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test C-side coil
        self.serialMock.expected_commands = {
            b'\x15\x08': None,      # enable A/C relay
            b'\x17\x01': None       # pulse coil 1
        }
        self.machine.coils["c_test1_c_side"].pulse(20)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # wait for A/C disable
        self.serialMock.expected_commands = {
            b'\x16\x08': None,      # disable A/C relay
        }
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test A-side coil
        self.serialMock.expected_commands = {
            b'\x17\x01': None       # pulse coil 1
        }
        self.machine.coils["c_test1_a_side"].pulse(20)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test C-side coil
        self.serialMock.expected_commands = {
            b'\x18\x01\x0f': None,  # set pulse_ms to 15ms
            b'\x17\x01': None       # pulse coil 1
        }
        self.machine.coils["c_test1_a_side"].pulse(15)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test C-side coil
        self.serialMock.expected_commands = {
            b'\x15\x08': None,      # enable A/C relay
            b'\x18\x01\x14': None,  # set pulse_ms to 20ms
            b'\x17\x01': None       # pulse coil 1
        }
        self.machine.coils["c_test1_c_side"].pulse(20)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # wait for A/C disable
        self.serialMock.expected_commands = {
            b'\x16\x08': None,      # disable A/C relay
        }
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)


class TestAPC(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/apc/'

    def _mock_loop(self):
        self.clock.mock_serial("com1", self.serialMock)

    def tearDown(self):
        self.assertFalse(self.serialMock.crashed)
        super().tearDown()

    def get_platform(self):
        return False

    def _wait_for_processing(self):
        start = time.time()
        while self.serialMock.expected_commands and not self.serialMock.crashed and time.time() < start + 10:
            self.advance_time_and_run(.01)

    def setUp(self):
        self.expected_duration = 1.5
        self.serialMock = MockLisySocket(api_version=9)

        self.serialMock.permanent_commands = {
            b'\x29': b'\x7F',           # changed switches? -> no
            b'\x65': b'\x00'            # watchdog
        }

        self.serialMock.expected_commands = {
            b'\x00': b'APC\00',         # hw APC
            b'\x01': b'0.02\00',        # APC version
            b'\x02': b'0.09\00',        # api version
            b'\x64': b'\x00',           # reset -> ok
            b'\x03': b'\x28',           # get number of lamps -> 40
            b'\x04': b'\x09',           # get number of solenoids -> 9
            b'\x06': b'\x05',           # get number of displays -> 5
            b'\x07\x00': b'\x02\x10',   # get type of display 0
            b'\x07\x01': b'\x03\x05',   # get type of display 1
            b'\x07\x02': b'\x04\x07',   # get type of display 2
            b'\x07\x03': b'\x05\x03',   # get type of display 3
            b'\x07\x04': b'\x06\x10',   # get type of display 4
            b'\x09': b'\x58',           # get number of switches -> 88
            b'\x13': b'\x00',           # get number of modern lights -> 0
            b'\x1e\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,  # clear display
            b'\x1f\x05\x00\x00\x00\x00\x00': None,                                              # clear display
            b'\x20\x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,          # clear display
            b'\x21\x03\x20\x20\x20': None,                                                      # clear display
            b'\x22\x10\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20': None,  # clear display
            b'\x19\x00\x0a': None,
            b'\x19\x01\x0a': None,
            b'\x19\x67\xff': None,
            b'\x19\x05\x1e': None,
            b'\x19\x06\x0a': None,
            b'\x19\x07\x0a': None,
        }

        for number in range(88):
            if number % 10 >= 8:
                self.serialMock.expected_commands[bytes([40, number])] = b'\x02'
            else:
                self.serialMock.expected_commands[bytes([40, number])] = b'\x00' if number != 37 else b'\x01'

        # prevent changes on real hardware
        lisy.LisyHardwarePlatform._disable_dts_on_start_of_serial = MagicMock()

        super().setUp()

        lisy.LisyHardwarePlatform._disable_dts_on_start_of_serial.assert_called_with()

        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def test_platform(self):
        # wait for watchdog
        self.serialMock.expected_commands = {
            b'\x65': b'\x00'            # watchdog
        }
        self._wait_for_processing()

        # test sound
        self.serialMock.expected_commands = {
            b'\x32\x01\x02': None
        }
        self.post_event("test2")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test sound on track 2
        self.serialMock.expected_commands = {
            b'\x32\x02\x05': None
        }
        self.post_event("test4")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test sound file
        self.serialMock.expected_commands = {
            b'\x34\x01\x00some_file\x00': None
        }
        self.post_event("play_file")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test sound file looping
        self.serialMock.expected_commands = {
            b'\x34\x01\x01some_file\x00': None
        }
        self.post_event("play_file_loop")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # text to speech
        self.serialMock.expected_commands = {
            b'\x35\x01\x02Hello MPF\x00': None
        }
        self.post_event("play_text")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set volume to 50 (32 hex)
        self.serialMock.expected_commands = {
            b'\x36\x01\x32': None
        }
        self.post_event("volume_05")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # increase volume by 0.1 -> 60 -> hex 3C
        self.serialMock.expected_commands = {
            b'\x36\x01\x3C': None
        }
        self.post_event("increase_volume")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # decrease volume by 0.01 -> 59 -> hex 3B
        self.serialMock.expected_commands = {
            b'\x36\x01\x3B': None
        }
        self.post_event("decrease_volume")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # test another sound
        self.serialMock.expected_commands = {
            b'\x32\x01\x03': None
        }
        self.post_event("test3")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # stop sound
        self.serialMock.expected_commands = {
            b'\x33\01': None
        }
        self.post_event("test_stop")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def test_rules(self):
        """Test HW Rules."""
        self.serialMock.expected_commands = {
            b'\x3c\x05\x01\x02\x00\x1e\xff\x00\x03\x02\x00': None,      # create rule for main
            b'\x3c\x06\x01\x00\x00\x0a\xff\xff\x03\x00\x00': None,      # create rule for hold
        }
        self.machine.flippers["f_test_hold_eos"].enable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x3c\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for main
            b'\x3c\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for hold
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

        # set info display to TEST
        self.serialMock.expected_commands = {
            b'\x1e\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x03\x03\x07': None
        }
        self.machine.segment_displays["info_display"].add_text("1337")
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


class TestLisyV10(MpfTestCase):

    def get_config_file(self):
        return 'config_modern.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/lisy/'

    def _mock_loop(self):
        self.clock.mock_serial("com1", self.serialMock)

    def tearDown(self):
        self.assertFalse(self.serialMock.crashed)
        super().tearDown()

    def get_platform(self):
        return False

    def _wait_for_processing(self):
        start = time.time()
        while self.serialMock.expected_commands and not self.serialMock.crashed and time.time() < start + 10:
            self.advance_time_and_run(.01)

    def setUp(self):
        self.expected_duration = 1.5
        self.serialMock = MockLisySocket(api_version=10)

        self.serialMock.permanent_commands = {
            b'\x29': b'\x7F',           # changed switches? -> no
            b'\x65': b'\x00'            # watchdog
        }

        self.serialMock.expected_commands = {
            b'\x00': b'FUTURE_HARDWARE\00',         # hw not known yet
            b'\x01': b'0.42\00',        # hardware version
            b'\x02': b'0.10\00',        # api version
            b'\x64': b'\x00',           # reset -> ok
            b'\x03': b'\x00',           # get number of simple lamps -> 0
            b'\x04': b'\x09',           # get number of solenoids -> 9
            b'\x06': b'\x00',           # get number of displays -> 0
            b'\x09': b'\x58',           # get number of switches -> 88
            b'\x13': b'\x02\x01',       # get number of modern lights -> 512 + 1 = 513 modern lights
            b'\x19\x00\x0a': None,
            b'\x19\x01\x0a': None,
            b'\x19\x05\x1e': None,
            b'\x19\x06\x0a': None,
            b'\x19\x07\x0a': None,
        }

        for number in range(88):
            if number % 10 >= 8:
                self.serialMock.expected_commands[bytes([40, number])] = b'\x02'
            else:
                self.serialMock.expected_commands[bytes([40, number])] = b'\x00' if number != 37 else b'\x01'

        # prevent changes on real hardware
        lisy.LisyHardwarePlatform._disable_dts_on_start_of_serial = MagicMock()

        super().setUp()

        lisy.LisyHardwarePlatform._disable_dts_on_start_of_serial.assert_called_with()

        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def test_rules(self):
        """Test HW Rules."""
        # wait for watchdog
        self.serialMock.expected_commands = {
            b'\x65': b'\x00'  # watchdog
        }
        self._wait_for_processing()

        self.serialMock.expected_commands = {
            b'\x3c\x05\x01\x02\x00\x1e\xff\x00\x03\x02\x00': None,      # create rule for main
            b'\x3c\x06\x01\x00\x00\x0a\xff\xff\x03\x00\x00': None,      # create rule for hold
        }
        self.machine.flippers["f_test_hold_eos"].enable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x3c\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for main
            b'\x3c\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for hold
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
