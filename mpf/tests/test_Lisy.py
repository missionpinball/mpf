import time

import sys

from mpf.platforms.lisy import lisy

from mpf.tests.MpfTestCase import MpfTestCase, test_config, MagicMock
from mpf.tests.loop import MockSerial, MockSocket


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
        if msg in self.permanent_commands and msg not in self.expected_commands:
            if self.permanent_commands[msg] is not None:
                self.queue.append(self.permanent_commands[msg])
            return len(msg)

        # print("Serial received: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
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

    def __init__(self):
        super().__init__()
        self.name = "SerialMock"
        self.expected_commands = {}
        self.queue = []
        self.permanent_commands = {}
        self.crashed = False


class TestLisy(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
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
        if sys.version_info[0] == 3 and sys.version_info[1] == 4:
            # this fails on python 3.4 because of some asyncio bugs
            self.skipTest("Test is unstable in Python 3.4")
            return
        self.expected_duration = 1.5
        self.serialMock = MockLisySocket()

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
            b'\x1e\x00': None,          # clear display
            b'\x1f\x00': None,          # clear display
            b'\x20\x00': None,          # clear display
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
            b'\x1ETEST\x00': None
        }
        self.machine.segment_displays["info_display"].add_text("TEST")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set player 1 display to 42000
        self.serialMock.expected_commands = {
            b'\x1F42000\x00': None
        }
        self.machine.segment_displays["player1_display"].add_text("42000")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set player 1 display to flashing
        self.serialMock.expected_commands = {
            b'\x1F42000\x00': None,
        }
        self.machine.segment_displays["player1_display"].set_flashing(True)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x1F42000\x00': None,
            b'\x1F\x00': None
        }

        self.advance_time_and_run(1)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x1F42000\x00': None,
        }
        self.machine.segment_displays["player1_display"].set_flashing(False)
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

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
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
        if sys.version_info[0] == 3 and sys.version_info[1] == 4:
            # this fails on python 3.4 because of some asyncio bugs
            self.skipTest("Test is unstable in Python 3.4")
            return
        self.expected_duration = 1.5
        self.serialMock = MockLisySocket()

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
            b'\x07\x00': b'\x10\x02',   # get type of display 0
            b'\x07\x01': b'\x05\x03',   # get type of display 1
            b'\x07\x02': b'\x07\x04',   # get type of display 2
            b'\x07\x03': b'\x03\x05',   # get type of display 3
            b'\x07\x04': b'\x10\x06',   # get type of display 4
            b'\x09': b'\x58',           # get number of switches -> 88
            b'\x13': b'\x00',           # get number of modern lights -> 0
            b'\x1e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,  # clear display
            b'\x1f\x00\x00\x00\x00\x00': None,                                              # clear display
            b'\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,          # clear display
            b'\x21\x20\x20\x20': None,                                                      # clear display
            b'\x22\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20': None,  # clear display
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
        }
        self.machine.autofires["ac_slingshot"].enable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands = {
            b'\x3c\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00': None,      # remove rule for slingshot
        }
        self.machine.autofires["ac_slingshot"].disable()
        self.advance_time_and_run(.2)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set info display to TEST
        self.serialMock.expected_commands = {
            b'\x1e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x03\x03\x07': None
        }
        self.machine.segment_displays["info_display"].add_text("1337")
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)
