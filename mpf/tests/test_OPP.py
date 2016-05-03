import copy
import time
from queue import Queue
from mpf.tests.MpfTestCase import MpfTestCase
from mock import MagicMock
from mpf.platforms import opp


class SerialMock:
    def read(self, length):
        del length
        if not self.send_buffer:
            msg = self.queue.get()
        else:
            msg = self.send_buffer.pop()
        return msg

    def write(self, msg):
        if msg in self.permanent_commands:
            self.send_buffer.append(self.permanent_commands[msg])
            return

        # print("Serial received: " + "".join("\\x%02x" % ord(b) for b in msg) + " len: " + str(len(msg)))
        if msg not in self.expected_commands:
            self.crashed = True
            raise AssertionError("Unexpected command: " + "".join("\\x%02x" % ord(b) for b in msg) +
                                 " len: " + str(len(msg)))

        if self.expected_commands[msg] is not False:
            self.send_buffer.append(self.expected_commands[msg])

        del self.expected_commands[msg]

    def __init__(self):
        self.name = "SerialMock"
        self.send_buffer = []
        self.expected_commands = {}
        self.queue = Queue()
        self.permanent_commands = {}
        self.crashed = False


class TestOPP(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/opp/'

    def _crc_message(self, msg, term=True):
        crc_msg = msg + opp.OppRs232Intf.calc_crc8_part_msg(msg, 0, len(msg))
        if term:
            crc_msg += '\xff'
        return crc_msg

    def setUp(self):
        opp.serial_imported = True
        opp.serial = MagicMock()
        self.serialMock = SerialMock()
        self.serialMock.send_buffer = []
        board1_config = '\x20\x0d\x01\x02\x03\x03'      # wing1: solenoids, wing2: inputs, wing3: lamps, wing4: lamps
        board2_config = '\x21\x0d\x06\x02\x02\x01'      # wing1: neo, wing2: inputs, wing3: inputs, wing4: solenoids
        board1_version = '\x20\x02\x00\x00\x10\x00'     # 0.0.16.0
        board2_version = '\x21\x02\x00\x00\x10\x01'     # 0.0.16.01
        inputs1_message = "\x20\x08\x00\x00\x00\x0c"     # inputs 0+1 off, 2+3 on, 8 on
        inputs2_message = "\x21\x08\x00\x00\x00\x00"

        self.serialMock.expected_commands = {
            '\xf0\xff': '\xf0\x20\x21\xff',     # boards 20 + 21 installed
            self._crc_message('\x20\x0d\x00\x00\x00\x00', False) + self._crc_message('\x21\x0d\x00\x00\x00\x00'):
                self._crc_message(board1_config, False) + self._crc_message(board2_config),     # get config
            self._crc_message('\x20\x02\x00\x00\x00\x00', False) + self._crc_message('\x21\x02\x00\x00\x00\x00'):
                self._crc_message(board1_version, False) + self._crc_message(board2_version),   # get version
            self._crc_message('\x20\x14\x00\x02\x17\x00'): False,   # configure coil 0
            self._crc_message('\x20\x14\x01\x00\x17\x0f'): False,   # configure coil 1
            self._crc_message('\x20\x14\x02\x00\x0a\x01'): False,   # configure coil 2
            self._crc_message('\x20\x14\x03\x00\x0a\x06'): False,    # configure coil 3
                                             }
        self.serialMock.permanent_commands = {
            '\xff': '\xff',
            self._crc_message('\x20\x08\x00\x00\x00\x00', False) + self._crc_message('\x21\x08\x00\x00\x00\x00'):
                self._crc_message(inputs1_message, False) + self._crc_message(inputs2_message),  # read inputs
        }
        opp.serial.Serial = MagicMock(return_value=self.serialMock)
        super(TestOPP, self).setUp()

        for i in range(10):
            self._write_message("\xff", False)

        self.assertFalse(self.serialMock.expected_commands)

    def tearDown(self):
        self.assertFalse(self.serialMock.crashed)
        super(TestOPP, self).tearDown()

    def get_platform(self):
        return 'opp'

    def _write_message(self, msg, crc=True):
        self.machine_run()
        if crc:
            self.serialMock.queue.put(self._crc_message(msg))
        else:
            self.serialMock.queue.put(msg)
        while not self.serialMock.queue.empty():
            time.sleep(.001)
            self.advance_time_and_run(1)

    def test_opp(self):
        self._test_coils()
        self._test_leds()
        self._test_matrix_lights()
        self._test_autofires()
        self._test_switches()
        self._test_flippers()

    def _test_switches(self):
        # initial switches
        self.assertTrue(self.machine.switch_controller.is_active("s_test"))
        self.assertTrue(self.machine.switch_controller.is_active("s_test_no_debounce"))
        self.assertTrue(self.machine.switch_controller.is_active("s_test_nc"))
        self.assertFalse(self.machine.switch_controller.is_active("s_flipper"))
        self.assertTrue(self.machine.switch_controller.is_active("s_test_card2"))

        # switch change
        permanent_commands = copy.deepcopy(self.serialMock.permanent_commands)

        inputs_message = "\x20\x08\x00\x00\x01\x08"  # inputs 0+1+2 off, 3 on, 8 off
        self.serialMock.permanent_commands = {
            '\xff': '\xff',
            self._crc_message('\x20\x08\x00\x00\x00\x00', False) + self._crc_message('\x21\x08\x00\x00\x00\x00'):
                self._crc_message(inputs_message)
        }
        for i in range(10):
            self._write_message("\xff", False)

        self.assertTrue(self.machine.switch_controller.is_active("s_test"))
        self.assertTrue(self.machine.switch_controller.is_active("s_test_no_debounce"))
        self.assertFalse(self.machine.switch_controller.is_active("s_test_nc"))
        self.assertFalse(self.machine.switch_controller.is_active("s_flipper"))
        self.assertFalse(self.machine.switch_controller.is_active("s_test_card2"))

        self.serialMock.permanent_commands = permanent_commands

    def _test_coils(self):
        # pulse coil
        self.serialMock.expected_commands[self._crc_message('\x20\x07\x00\x01\x00\x01', False)] = False
        self.machine.coils.c_test.pulse()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

        # enable coil (not allowed)
        with self.assertRaises(AssertionError):
            self.machine.coils.c_test.enable()

        # disable coil
        self.serialMock.expected_commands[self._crc_message('\x20\x07\x00\x00\x00\x01', False)] = False
        self.machine.coils.c_test.disable()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

        # pulse coil (with allow_enable set)
        self.serialMock.expected_commands[self._crc_message('\x20\x14\x01\x02\x17\x00')] = False
        self.serialMock.expected_commands[self._crc_message('\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils.c_test_allow_enable.pulse()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

        # enable coil (with allow_enable set)
        self.serialMock.expected_commands[self._crc_message('\x20\x14\x01\x00\x17\x0f')] = False
        self.serialMock.expected_commands[self._crc_message('\x20\x07\x00\x02\x00\x02', False)] = False
        self.machine.coils.c_test_allow_enable.enable()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

    def _test_matrix_lights(self):
        self.serialMock.expected_commands[self._crc_message('\x20\x13\x07\x00\x01\x00\x00')] = False
        self.machine.lights.test_light1.on()
        self.machine.lights.test_light2.off()
        # it will only update once every 10 ticks so just advance 10 times to be sure
        for i in range(10):
            self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message('\x20\x13\x07\x00\x03\x00\x00')] = False
        self.machine.lights.test_light1.on()
        self.machine.lights.test_light2.on()
        # it will only update once every 10 ticks so just advance 10 times to be sure
        for i in range(10):
            self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

    def _test_leds(self):
        # add ff/ff/ff as color 0
        self.serialMock.expected_commands[self._crc_message('\x21\x11\x00\xff\xff\xff', False)] = False
        # set led 0 to color 0
        self.serialMock.expected_commands[self._crc_message('\x21\x16\x00\x80', False)] = False

        self.machine.leds.test_led1.on()
        for i in range(10):
            self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

        # add 00/00/00 as color 1
        self.serialMock.expected_commands[self._crc_message('\x21\x11\x01\x00\x00\x00', False)] = False
        # set led 0 to color 1
        self.serialMock.expected_commands[self._crc_message('\x21\x16\x00\x81', False)] = False
        # set led 1 to color 10
        self.serialMock.expected_commands[self._crc_message('\x21\x16\x01\x80', False)] = False

        self.machine.leds.test_led1.off()
        self.machine.leds.test_led2.on()
        for i in range(10):
            self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

    def _test_autofires(self):
        self.serialMock.expected_commands[self._crc_message('\x20\x14\x00\x03\x17\x00')] = False
        self.machine.autofires.ac_slingshot_test.enable()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message('\x20\x14\x00\x02\x17\x00')] = False
        self.machine.autofires.ac_slingshot_test.disable()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

    def _test_flippers(self):
        self.serialMock.expected_commands[self._crc_message('\x20\x14\x03\x01\x0a\x06')] = False
        self.machine.flippers.f_test_single.enable()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)

        self.serialMock.expected_commands[self._crc_message('\x20\x14\x03\x00\x0a\x06')] = False
        self.machine.flippers.f_test_single.disable()
        self._write_message("\xff", False)
        self.assertFalse(self.serialMock.expected_commands)
