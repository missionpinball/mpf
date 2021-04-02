import copy
import logging

from mpf.platforms.opp.opp import OppHardwarePlatform
from unittest.mock import MagicMock

import time

from mpf.platforms.opp import opp
from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSerial

COMMAND_LENGTH = {
    0x00: 7,
    0x02: 7,
    0x07: 7,
    0x08: 7,
    0x0d: 7,
    0x13: 8,
    0x14: 7,
    0x17: 5,
    0x19: 11,
}

class MockOppSocket(MockSerial):

    def read(self, length):
        del length
        if not self.queue:
            return b""
        msg = b""
        while self.queue:
            msg += self.queue.pop(0)
        return msg

    def read_ready(self):
        return bool(self.queue)

    def write_ready(self):
        return True

    def write(self, msg):
        """Handle messages in fake OPP."""
        #print("Serial received: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
        total_msg_len = len(msg)
        if self.crashed:
            return

        while msg:
            # special case: EOM and inventory map
            if msg[0] in (0xff, 0xf0):
                self._handle_msg(msg[0:1])
                msg = msg[1:]
                continue

            if len(msg) < 2:
                raise AssertionError("Message too short. " + "".join("\\x%02x" % b for b in msg))

            command = msg[1]
            if command == 0x40:
                # special case of variable length message
                if len(msg) < 6:
                    raise AssertionError("Fade too short. " + "".join("\\x%02x" % b for b in msg))
                command_len = 9 + msg[5]
            else:
                if command not in COMMAND_LENGTH:
                    raise AssertionError("Unknown command. " + "".join("\\x%02x" % b for b in msg))
                command_len = COMMAND_LENGTH[command]

            if len(msg) < command_len:
                raise AssertionError("Command length ({}) does not match message length ({}). {}".format(
                    command_len, len(msg), "".join("\\x%02x" % b for b in msg)
                ))

            self._handle_msg(msg[0:command_len])
            msg = msg[command_len:]

        return total_msg_len

    def _handle_msg(self, msg):
        # print("Handling: " + "".join("\\x%02x" % b for b in msg) + " len: " + str(len(msg)))
        if msg in self.permanent_commands:
            self.queue.append(self.permanent_commands[msg])
            return len(msg)

        if msg not in self.expected_commands:
            self.crashed = True
            remaining_expected_commands = dict(self.expected_commands)
            self.expected_commands = {"crashed": True}
            raise AssertionError("Unexpected command: " + "".join("\\x%02x" % b for b in msg) +
                                 " len: " + str(len(msg)) + " Remaining expected commands: " +
                                 str(remaining_expected_commands) + " on " + self.name)

        if self.expected_commands[msg] is not False:
            self.queue.append(self.expected_commands[msg])

        del self.expected_commands[msg]

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.expected_commands = {}
        self.queue = []
        self.permanent_commands = {}
        self.crashed = False


class OPPCommon(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        self.expected_duration = 2
        self.serialMock = None

    def get_machine_path(self):
        return 'tests/machine_files/opp/'

    def _crc_message(self, msg, term=False):
        crc_msg = msg + OppRs232Intf.calc_crc8_part_msg(msg, 0, len(msg))
        if term:
            crc_msg += b'\xff'
        return crc_msg

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

        self.assertFalse(self.serialMock.crashed)


class TestOPPStm32(MpfTestCase):

    def __init__(self, methodName):
        super().__init__(methodName)
        self.expected_duration = 2
        self.serialMocks = {}

    def get_machine_path(self):
        return 'tests/machine_files/opp/'

    def _crc_message(self, msg, term=False):
        crc_msg = msg + OppRs232Intf.calc_crc8_part_msg(msg, 0, len(msg))
        if term:
            crc_msg += b'\xff'
        return crc_msg

    def _mock_loop(self):
        self.clock.mock_serial("com1", self.serialMocks["com1"])
        self.clock.mock_serial("com2", self.serialMocks["com2"])

    def tearDown(self):
        for port, mock in self.serialMocks.items():
            self.assertFalse(mock.crashed, "Mock {} crashed".format(port))
        super().tearDown()

    def get_platform(self):
        return False

    def _wait_for_processing(self):
        start = time.time()
        while sum([len(mock.expected_commands) for mock in self.serialMocks.values()]) and \
                not sum([mock.crashed for mock in self.serialMocks.values()]) and time.time() < start + 10:
            self.advance_time_and_run(.01)
        self.assertFalse(self.serialMocks["com1"].expected_commands)
        self.assertFalse(self.serialMocks["com2"].expected_commands)

    def get_config_file(self):
        return 'config_stm32.yaml'

    def setUp(self):
        self.expected_duration = 1.5
        opp.serial_imported = True
        opp.serial = MagicMock()
        self.serialMocks["com1"] = MockOppSocket("com1")
        self.serialMocks["com2"] = MockOppSocket("com2")
        board1_config = b'\x20\x0d\x01\x02\x03\x08'      # wing1: solenoids, wing2: inputs, wing3: lamps, wing4: neo_sol
        board2_config = b'\x20\x0d\x0b\x0c\x03\x03'      # wing1: lamps, wing2: lamps, wing3: lamps, wing4: lamps
        board1_version = b'\x20\x02\x02\x01\x00\x00'     # 2.1.0.0
        board2_version = b'\x20\x02\x02\x01\x00\x00'     # 2.1.0.0
        inputs1_message = b"\x20\x08\x00\xff\x00\x0c"    # inputs 0+1 off, 2+3 on, 8 on
        inputs2_message = b"\x20\x08\x00\x00\x00\x00"

        self.serialMocks["com1"].expected_commands = {
            b'\xf0': b'\xf0\x20',     # boards 20 installed
            self._crc_message(b'\x20\x0d\x00\x00\x00\x00'): self._crc_message(board1_config), # get config
            self._crc_message(b'\x20\x02\x00\x00\x00\x00'): self._crc_message(board1_version),   # get version
            self._crc_message(b'\x20\x00\x00\x00\x00\x00'): self._crc_message(b'\x20\x00\x01\x23\x45\x67'),
            self._crc_message(b'\x20\x40\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00'): False
        }
        self.serialMocks["com1"].permanent_commands = {
            b'\xff': b'\xff',
            self._crc_message(b'\x20\x08\x00\x00\x00\x00'): self._crc_message(inputs1_message),  # read inputs
        }

        self.serialMocks["com2"].expected_commands = {
            b'\xf0': b'\xf0\x20',     # boards 20 installed
            self._crc_message(b'\x20\x0d\x00\x00\x00\x00'): self._crc_message(board2_config), # get config
            self._crc_message(b'\x20\x02\x00\x00\x00\x00'): self._crc_message(board2_version),   # get version
            self._crc_message(b'\x20\x00\x00\x00\x00\x00'): self._crc_message(b'\x20\x00\x00\x00\x00\x02'),
            self._crc_message(b'\x20\x40\x10\x10\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'): False,
            self._crc_message(b'\x20\x40\x10\x1f\x00\x01\x00\x00\x00'): False,
            self._crc_message(b'\x20\x40\x20\x00\x00\x02\x00\x00\x00\x00'): False,
            self._crc_message(b'\x20\x40\x20\x3f\x00\x01\x00\x00\x00'): False,
        }
        self.serialMocks["com2"].permanent_commands = {
            b'\xff': b'\xff',
            self._crc_message(b'\x20\x08\x00\x00\x00\x00'): self._crc_message(inputs2_message),  # read inputs
        }
        super().setUp()

        assert isinstance(self.machine.default_platform, OppHardwarePlatform)

        self._wait_for_processing()
        self.assertEqual(0x02010000, self.machine.default_platform.min_version["19088743"])
        self.assertEqual(0x02010000, self.machine.default_platform.min_version["2"])

        self.maxDiff = 100000

        # test hardware scan
        info_str = """Connected CPUs:
 - Port: com1 at 115200 baud. Chain Serial: 19088743
 -> Board: 0x20 Firmware: 0x2010000
 - Port: com2 at 115200 baud. Chain Serial: 2
 -> Board: 0x20 Firmware: 0x2010000

Incand cards:
 - Chain: 19088743 Board: 0x20 Card: 0 Numbers: [16, 17, 18, 19, 20, 21, 22, 23]
 - Chain: 2 Board: 0x20 Card: 0 Numbers: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]

Input cards:
 - Chain: 19088743 Board: 0x20 Card: 0 Numbers: [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 25, 26, 27]

Solenoid cards:
 - Chain: 19088743 Board: 0x20 Card: 0 Numbers: [0, 1, 2, 3, 12, 13, 14, 15]

LEDs:
 - Chain: 19088743 Board: 0x20 Card: 0
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def testOpp(self):
        # assert that the watchdog does not trigger on incand only boards
        with self.assertLogs('OPP', level='WARNING') as cm:
            self.advance_time_and_run(1)
            self.assertFalse(cm.output)
            # log something to prevent the test from breaking
            logging.getLogger("OPP").warning("DEBUG")

        # set color of neo pixel
        self.serialMocks["com1"].expected_commands[
            self._crc_message(b'\x20\x40\x00\x00\x00\x06\x00\x64\xff\x00\x00\x00\x00\xff', False)] = False
        self.machine.lights["l_neo_0"].color("red", fade_ms=100)
        self.machine.lights["l_neo_1"].color("blue", fade_ms=100)
        self.advance_time_and_run(.01)
        self._wait_for_processing()

        self.advance_time_and_run(.15)

        self.serialMocks["com1"].expected_commands[
            self._crc_message(b'\x20\x40\x00\x00\x00\x06\x00\x64\x00\x00\xff\xff\x00\x00', False)] = False
        self.machine.lights["l_neo_0"].color("blue", fade_ms=100)
        self.machine.lights["l_neo_1"].color("red", fade_ms=100)
        self.advance_time_and_run(.01)
        self._wait_for_processing()

        self.advance_time_and_run(.15)

        self.machine.lights["l_neo_0"].color("blue", fade_ms=100)
        self.machine.lights["l_neo_1"].color("red", fade_ms=100)
        self.advance_time_and_run(.01)
        self._wait_for_processing()

        self.serialMocks["com2"].expected_commands[
            self._crc_message(b'\x20\x40\x10\x13\x00\x02\x00\x64\x99\xe5', False)] = False

        self.machine.lights["l2-3"].color("white%60", fade_ms=100)
        self.machine.lights["l2-4"].color("white%90", fade_ms=100)
        self.advance_time_and_run(.02)
        self._wait_for_processing()

        self.serialMocks["com2"].expected_commands[
            self._crc_message(b'\x20\x40\x20\x00\x00\x02\x00\x64\x99\xe5', False)] = False

        self.machine.lights["m0-0"].color("white%60", fade_ms=100)
        self.machine.lights["m0-1"].color("white%90", fade_ms=100)
        self.advance_time_and_run(.02)
        self._wait_for_processing()


class TestOPPFirmware2(OPPCommon, MpfTestCase):

    def get_config_file(self):
        return 'config2.yaml'

    def setUp(self):
        self.expected_duration = 1.5
        opp.serial_imported = True
        opp.serial = MagicMock()
        self.serialMock = MockOppSocket("com1")
        board1_config = b'\x20\x0d\x01\x02\x03\x03'     # wing1: solenoids, wing2: inputs, wing3: lamps, wing4: lamps
        board2_config = b'\x21\x0d\x06\x02\x02\x01'     # wing1: neo, wing2: inputs, wing3: inputs, wing4: solenoids
        board3_config = b'\x22\x0d\x03\x03\x03\x07'     # wing1: lamps, wing2: lamps, wing3: lamps, wing4: hi-side lamps
        board4_config = b'\x23\x0d\x01\x01\x04\x05'     # wing1: sol, wing2: sol, wing3: matrix_out, wing4: matrix_in
        board1_version = b'\x20\x02\x02\x00\x00\x00'    # 2.0.0.0
        board2_version = b'\x21\x02\x02\x00\x00\x00'    # 2.0.0.0
        board3_version = b'\x22\x02\x02\x00\x00\x00'    # 2.0.0.0
        board4_version = b'\x23\x02\x02\x00\x00\x00'    # 2.0.0.0
        inputs1_message = b"\x20\x08\x00\xff\x00\x0c"   # inputs 0+1 off, 2+3 on, 8 on
        inputs2_message = b"\x21\x08\x00\x00\x00\x00"
        inputs3a_message = b"\x23\x08\x00\x00\x00\x00"
        inputs3b_message = b"\x23\x19\x00\x00\x00\x00\x00\x00\x00\x01"

        self.serialMock.expected_commands = {
            b'\xf0': b'\xf0\x20\x21\x22\x23',     # boards 20 + 21 + 22 + 23 installed
            self._crc_message(b'\x20\x0d\x00\x00\x00\x00'): self._crc_message(board1_config),
            self._crc_message(b'\x21\x0d\x00\x00\x00\x00'): self._crc_message(board2_config),
            self._crc_message(b'\x22\x0d\x00\x00\x00\x00'): self._crc_message(board3_config),
            self._crc_message(b'\x23\x0d\x00\x00\x00\x00'): self._crc_message(board4_config), # get config
            self._crc_message(b'\x20\x02\x00\x00\x00\x00'): self._crc_message(board1_version),
            self._crc_message(b'\x21\x02\x00\x00\x00\x00'): self._crc_message(board2_version),
            self._crc_message(b'\x22\x02\x00\x00\x00\x00'): self._crc_message(board3_version),
            self._crc_message(b'\x23\x02\x00\x00\x00\x00'): self._crc_message(board4_version),   # get version
            self._crc_message(b'\x20\x14\x00\x02\x17\x00'): False,  # configure coil 0
            self._crc_message(b'\x20\x14\x01\x04\x17\x00'): False,  # configure coil 1
            self._crc_message(b'\x20\x14\x02\x04\x0a\x00'): False,  # configure coil 2
            self._crc_message(b'\x20\x14\x03\x00\x0a\x06'): False,  # configure coil 3
            self._crc_message(b'\x21\x14\x0c\x00\x0a\x01'): False,  # configure coil 1-12
            self._crc_message(b'\x23\x14\x00\x02\x2a\x00'): False,  # configure coil 3-0
            self._crc_message(b'\x20\x13\x07\x00\x00\x00\x00', False): False,  # turn off all incands
            self._crc_message(b'\x22\x13\x07\x00\x00\x00\x00', False): False,  # turn off all incands
            self._crc_message(b'\x21\x40\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00'): False,  # turn off leds
        }
        self.serialMock.permanent_commands = {
            b'\xff': b'\xff',
            self._crc_message(b'\x20\x08\x00\x00\x00\x00'): self._crc_message(inputs1_message),
            self._crc_message(b'\x21\x08\x00\x00\x00\x00'): self._crc_message(inputs2_message),
            self._crc_message(b'\x23\x08\x00\x00\x00\x00'): self._crc_message(inputs3a_message),
            self._crc_message(b'\x23\x19\x00\x00\x00\x00\x00\x00\x00\x00'): self._crc_message(inputs3b_message),  # read inputs
        }
        super().setUp()

        assert isinstance(self.machine.default_platform, OppHardwarePlatform)

        self._wait_for_processing()
        self.assertEqual(0x02000000, self.machine.default_platform.min_version["com1"])

        self.assertFalse(self.serialMock.expected_commands)
        self.maxDiff = 100000

        # test hardware scan
        info_str = """Connected CPUs:
 - Port: com1 at 115200 baud. Chain Serial: com1
 -> Board: 0x20 Firmware: 0x2000000
 -> Board: 0x21 Firmware: 0x2000000
 -> Board: 0x22 Firmware: 0x2000000
 -> Board: 0x23 Firmware: 0x2000000

Incand cards:
 - Chain: com1 Board: 0x20 Card: 0 Numbers: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
 - Chain: com1 Board: 0x22 Card: 2 Numbers: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,\
 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]

Input cards:
 - Chain: com1 Board: 0x20 Card: 0 Numbers: [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15]
 - Chain: com1 Board: 0x21 Card: 1 Numbers: [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,\
 22, 23, 24, 25, 26, 27]
 - Chain: com1 Board: 0x23 Card: 3 Numbers: [0, 1, 2, 3, 8, 9, 10, 11]
 - Chain: com1 Board: 0x23 Card: 3 Numbers: [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,\
 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78,\
 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95]

Solenoid cards:
 - Chain: com1 Board: 0x20 Card: 0 Numbers: [0, 1, 2, 3]
 - Chain: com1 Board: 0x21 Card: 1 Numbers: [12, 13, 14, 15]
 - Chain: com1 Board: 0x23 Card: 3 Numbers: [0, 1, 2, 3, 4, 5, 6, 7]

LEDs:
 - Chain: com1 Board: 0x21 Card: 1
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def testOpp(self):
        self._test_dual_wound_coils()
        self._test_switches()

    def _test_switches(self):
        # initial switches
        self.assertSwitchState("s_test", 1)
        self.assertSwitchState("s_test_no_debounce", 1)
        self.assertSwitchState("s_test_nc", 1)
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_test_card2", 1)
        self.assertSwitchState("s_matrix_test", 1)
        self.assertSwitchState("s_matrix_test2", 0)
        self.assertSwitchState("s_matrix_test3", 1)

        # switch change
        permanent_commands = copy.deepcopy(self.serialMock.permanent_commands)

        inputs1_message = b"\x20\x08\x00\x00\x01\x08"  # inputs 0+1+2 off, 3 on, 8 off
        inputs2_message = b'\x21\x08\x00\x00\x00\x00'
        inputs3a_message = b"\x23\x08\x00\x00\x00\x00"
        inputs3b_message = b"\x23\x19\x80\x00\x00\x00\x00\x01\x00\x00"
        self.serialMock.permanent_commands = {
            b'\xff': b'\xff',
            self._crc_message(b'\x20\x08\x00\x00\x00\x00'): self._crc_message(inputs1_message),
            self._crc_message(b'\x21\x08\x00\x00\x00\x00'): self._crc_message(inputs2_message),
            self._crc_message(b'\x23\x08\x00\x00\x00\x00'): self._crc_message(inputs3a_message),
            self._crc_message(b'\x23\x19\x00\x00\x00\x00\x00\x00\x00\x00'): self._crc_message(inputs3b_message),
        }

        switch = self.machine.switches["s_test_nc"]
        while self.machine.switch_controller.is_active(switch):
            self.advance_time_and_run(0.1)

        self.assertSwitchState("s_test", 1)
        self.assertSwitchState("s_test_no_debounce", 1)
        self.assertSwitchState("s_test_nc", 0)
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_test_card2", 0)
        self.assertSwitchState("s_matrix_test", 0)
        self.assertSwitchState("s_matrix_test2", 1)
        self.assertSwitchState("s_matrix_test3", 0)

        self.serialMock.permanent_commands = permanent_commands

    def _test_dual_wound_coils(self):
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x02\x24\x0a\x00')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x23\x0a\x00')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x17\x03\x03')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x17\x03\x02')] = False
        self.machine.flippers["f_test_hold"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # enable a coil (when a rule is active)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x21\x0a\x06')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x08\x00\x08', False)] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x23\x0a\x00')] = False
        self.machine.coils["c_flipper_main"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse it (when rule is active)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x08\x00\x08', False)] = False
        self.machine.coils["c_flipper_main"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse it with other settings (when rule is active)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x23\x2a\x00')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x08\x00\x08', False)] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x23\x0a\x00')] = False
        self.machine.coils["c_flipper_main"].pulse(42)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x02\x04\x0a\x20')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x00\x0a\x26')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x17\x03\x83')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x17\x03\x82')] = False
        self.machine.flippers["f_test_hold"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # enable a coil (which is already configured right)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils["c_test_allow_enable"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # disable it
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x00\x00\x02', False)] = False
        self.machine.coils["c_test_allow_enable"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse it
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x01\x02\x17\x00')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils["c_test_allow_enable"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse it again with same settings (no reconfigure)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils["c_test_allow_enable"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse it with other settings (should reconfigure)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x01\x02\x2a\x00')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils["c_test_allow_enable"].pulse(42)
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)


class TestOPP(OPPCommon, MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def setUp(self):
        self.expected_duration = 1.5
        opp.serial_imported = True
        opp.serial = MagicMock()
        self.serialMock = MockOppSocket("com1")
        board1_config = b'\x20\x0d\x01\x02\x03\x03'      # wing1: solenoids, wing2: inputs, wing3: lamps, wing4: lamps
        board2_config = b'\x21\x0d\x06\x02\x02\x01'      # wing1: neo, wing2: inputs, wing3: inputs, wing4: solenoids
        board1_version = b'\x20\x02\x00\x01\x01\x00'     # 0.1.1.0
        board2_version = b'\x21\x02\x00\x01\x01\x00'     # 0.1.1.0
        inputs1_message = b'\x20\x08\x00\x00\x00\x0c'    # inputs 0+1 off, 2+3 on, 8 on
        inputs2_message = b'\x21\x08\x00\x00\x00\x00'

        self.serialMock.expected_commands = {
            b'\xf0': b'\xf0\x20\x21',     # boards 20 + 21 installed
            self._crc_message(b'\x20\x0d\x00\x00\x00\x00'): self._crc_message(board1_config),
            self._crc_message(b'\x21\x0d\x00\x00\x00\x00'): self._crc_message(board2_config),     # get config
            self._crc_message(b'\x20\x02\x00\x00\x00\x00'): self._crc_message(board1_version),
            self._crc_message(b'\x21\x02\x00\x00\x00\x00'): self._crc_message(board2_version),   # get version
            self._crc_message(b'\x20\x14\x00\x02\x17\x00'): False,  # configure coil 0
            self._crc_message(b'\x20\x14\x01\x00\x17\x0f'): False,  # configure coil 1
            self._crc_message(b'\x20\x14\x02\x00\x0a\x0f'): False,  # configure coil 2
            self._crc_message(b'\x20\x14\x03\x00\x0a\x06'): False,  # configure coil 3
            self._crc_message(b'\x21\x14\x0c\x00\x0a\x01'): False,  # configure coil 1-12
            self._crc_message(b'\x20\x13\x07\x00\x00\x00\x00'): False,  # turn off all incands
            self._crc_message(b'\x21\x40\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00'): False   # turn off leds
        }
        self.serialMock.permanent_commands = {
            b'\xff': b'\xff',
            self._crc_message(b'\x20\x08\x00\x00\x00\x00'): self._crc_message(inputs1_message),
            self._crc_message(b'\x21\x08\x00\x00\x00\x00'): self._crc_message(inputs2_message),  # read inputs
        }
        super().setUp()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)

    def test_opp(self):
        self._test_coils()
        self._test_leds()
        self._test_matrix_lights()
        self._test_autofire_coils()
        self._test_switches()
        self._test_flippers()

        # test hardware scan
        self.maxDiff = 100000
        info_str = """Connected CPUs:
 - Port: com1 at 115200 baud. Chain Serial: com1
 -> Board: 0x20 Firmware: 0x10100
 -> Board: 0x21 Firmware: 0x10100

Incand cards:
 - Chain: com1 Board: 0x20 Card: 0 Numbers: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]

Input cards:
 - Chain: com1 Board: 0x20 Card: 0 Numbers: [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15]
 - Chain: com1 Board: 0x21 Card: 1 Numbers: [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]

Solenoid cards:
 - Chain: com1 Board: 0x20 Card: 0 Numbers: [0, 1, 2, 3]
 - Chain: com1 Board: 0x21 Card: 1 Numbers: [12, 13, 14, 15]

LEDs:
 - Chain: com1 Board: 0x21 Card: 1
"""
        self.assertEqual(info_str, self.machine.default_platform.get_info_string())

    def _test_switches(self):
        # initial switches
        self.assertSwitchState("s_test", 1)
        self.assertSwitchState("s_test_no_debounce", 1)
        self.assertSwitchState("s_test_nc", 1)
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_test_card2", 1)

        # switch change
        permanent_commands = copy.deepcopy(self.serialMock.permanent_commands)

        inputs1_message = b"\x20\x08\x00\x00\x01\x08"  # inputs 0+1+2 off, 3 on, 8 off
        inputs2_message = b'\x21\x08\x00\x00\x00\x00'
        self.serialMock.permanent_commands = {
            b'\xff': b'\xff',
            self._crc_message(b'\x20\x08\x00\x00\x00\x00'): self._crc_message(inputs1_message),
            self._crc_message(b'\x21\x08\x00\x00\x00\x00'): self._crc_message(inputs2_message)
        }

        switch = self.machine.switches["s_test_nc"]
        while self.machine.switch_controller.is_active(switch):
            self.advance_time_and_run(0.1)

        self.assertSwitchState("s_test", 1)
        self.assertSwitchState("s_test_no_debounce", 1)
        self.assertSwitchState("s_test_nc", 0)
        self.assertSwitchState("s_flipper", 0)
        self.assertSwitchState("s_test_card2", 0)

        self.serialMock.permanent_commands = permanent_commands

    def _test_coils(self):
        self.assertEqual("OPP com1 Board 0x20", self.machine.coils["c_test"].hw_driver.get_board_name())
        # pulse coil
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x00\x02\x17\x00')] = False   # configure coil 0
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x01\x00\x01')] = False
        self.machine.coils["c_test"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x21\x14\x0c\x02\x0a\x00')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x21\x07\x10\x00\x10\x00')] = False
        self.machine.coils["c_holdpower_16"].pulse(10)

        # enable coil (not allowed)
        with self.assertRaises(AssertionError):
            self.machine.coils["c_test"].enable()
        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)
        self.assertFalse(self.serialMock.crashed)

        # disable coil
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x00\x00\x01', False)] = False
        self.machine.coils["c_test"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # pulse coil (with allow_enable set)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x01\x02\x17\x00')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils["c_test_allow_enable"].pulse()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # enable coil (with allow_enable set)
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x01\x00\x17\x0f')] = False
        self.serialMock.expected_commands[self._crc_message(b'\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils["c_test_allow_enable"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def _test_matrix_lights(self):
        self.serialMock.expected_commands[self._crc_message(b'\x20\x13\x07\x00\x01\x00\x00', False)] = False
        self.machine.lights["test_light1"].on()
        self.machine.lights["test_light2"].off()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x13\x07\x00\x03\x00\x00', False)] = False
        self.machine.lights["test_light1"].on()
        self.machine.lights["test_light2"].on()
        # it will only update once every 10 ticks so just advance 10 times to be sure
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def _test_leds(self):
        # set leds 0, 1, 2 to brightness 255
        self.serialMock.expected_commands[self._crc_message(b'\x21\x40\x00\x00\x00\x03\x00\x00\xff\xff\xff', False)] = False

        self.machine.lights["test_led1"].on()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        # set leds 0, 1, 2 to brightness 0
        # set leds 3, 4, 5 to brightness 255
        self.serialMock.expected_commands[self._crc_message(b'\x21\x40\x00\x00\x00\x06\x00\x00\x00\x00\x00\xff\xff\xff', False)] = False

        self.machine.lights["test_led1"].off()
        self.machine.lights["test_led2"].on()

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)

        # align with update task
        self.advance_time_and_run(.1)

        # two fades which are close enough together are batched
        self.serialMock.expected_commands[self._crc_message(b'\x21\x40\x00\x00\x00\x06\x00\x64\xff\x00\x00\xff\x00\x00', False)] = False
        self.machine.lights["test_led1"].color("red", fade_ms=100)
        self.machine.lights["test_led2"].color("red", fade_ms=95)

        # align with update task
        self.advance_time_and_run(.1)

        # fade leds 3, 4, 5 to brightness 245, 222, 179
        self.serialMock.expected_commands[self._crc_message(b'\x21\x40\x00\x03\x00\x03\x07\xd0\xf5\xde\xb3', False)] = False

        self.machine.lights["test_led2"].color("wheat", fade_ms=2000)

        self._wait_for_processing()

        self.assertFalse(self.serialMock.expected_commands)

    def _test_autofire_coils(self):
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x00\x03\x17\x20')] = False
        self.machine.autofire_coils["ac_slingshot_test"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x00\x02\x17\x20')] = False
        self.machine.autofire_coils["ac_slingshot_test"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x01\x03\x17\x30')] = False
        self.machine.autofire_coils["ac_slingshot_test2"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x01\x00\x17\x3f')] = False
        self.machine.autofire_coils["ac_slingshot_test2"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x00\x0b\x17\x14')] = False
        self.machine.autofire_coils["ac_delayed_kickback"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x00\x02\x17\x20')] = False
        self.machine.autofire_coils["ac_delayed_kickback"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

    def _test_flippers(self):
        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x21\x0a\x06')] = False
        self.machine.flippers["f_test_single"].enable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message(b'\x20\x14\x03\x00\x0a\x26')] = False
        self.machine.flippers["f_test_single"].disable()
        self._wait_for_processing()
        self.assertFalse(self.serialMock.expected_commands)
