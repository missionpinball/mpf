import serial


class TMCLError(Exception):
    pass


def encode_request_command(m_address, n_command, n_type, n_motor, value, debug=False):
    # convert to bytes
    m_address = int(m_address) % (1 << 8)
    n_command = int(n_command) % (1 << 8)
    n_type = int(n_type) % (1 << 8)
    n_motor = int(n_motor) % (1 << 8)
    value = [(int(value) >> i * 8) % (1 << 8) for i in range(3, -1, -1)]
    # generate command
    checksum = (m_address + n_command + n_type + n_motor + sum(value)) % (1 << 8)
    tmcl_bytes = [m_address, n_command, n_type, n_motor] + value + [checksum]
    # tmcl_cmd = sum(b << (8 - i) * 8 for i, b in enumerate(tmcl_bytes))
    # if debug:
    #    print "{0:>18X}".format(tmcl_cmd), "".join([chr(b) for b in tmcl_bytes])
    return "".join([chr(b) for b in tmcl_bytes])


def encode_reply_command(r_address, m_address, status, n_command, value, debug=False):
    # convert to bytes
    r_address = int(r_address) % (1 << 8)
    m_address = int(m_address) % (1 << 8)
    status = int(status) % (1 << 8)
    n_command = int(n_command) % (1 << 8)
    value = [(int(value) >> i * 8) % (1 << 8) for i in range(3, -1, -1)]
    # generate command
    checksum = (r_address + m_address + status + n_command + sum(value)) % (1 << 8)
    tmcl_bytes = [r_address, m_address, status, n_command] + value + [checksum]
    # tmcl_cmd = sum(b << (8 - i) * 8 for i, b in enumerate(tmcl_bytes))
    # if debug:
    #    print "{0:>18X}".format(tmcl_cmd), "".join([chr(b) for b in tmcl_bytes])
    return "".join([chr(b) for b in tmcl_bytes])


def decode_request_command(cmd_string):
    byte_array = bytearray(cmd_string)
    if len(byte_array) != 9:
        raise TMCLError("Commandstring shorter than 9 bytes")
    if byte_array[8] != sum(byte_array[:8]) % (1 << 8):
        raise TMCLError("Checksum error in command %s" % cmd_string)
    ret = {'module-address': byte_array[0], 'command-number': byte_array[1], 'type-number': byte_array[2],
           'motor-number': byte_array[3], 'value': sum(b << (3 - i) * 8 for i, b in enumerate(byte_array[4:8])),
           'checksum': byte_array[8]}
    return ret


def decode_reply_command(cmd_string):
    byte_array = bytearray(cmd_string)
    if len(byte_array) != 9:
        raise TMCLError("Commandstring shorter than 9 bytes")
    if byte_array[8] != sum(byte_array[:8]) % (1 << 8):
        raise TMCLError("Checksum error in command %s" % cmd_string)
    ret = {'reply-address': byte_array[0], 'module-address': byte_array[1], 'status': byte_array[2],
           'command-number': byte_array[3], 'value': sum(b << (3 - i) * 8 for i, b in enumerate(byte_array[4:8])),
           'checksum': byte_array[8]}
    return ret


STATUS_CODES = {100: "Succesfully executed, no error",
                101: "Command loaded into TMCL program EEPROM",
                1: "Wrong Checksum",
                2: "Invalid command",
                3: "Wrong type",
                4: "Invalid value",
                5: "Configuration EEPROM locked",
                6: "Command not available"}

STAT_OK = 100

COMMAND_NUMBERS = {1: "ROR", 2: "ROL", 3: "MST",
                   4: "MVP", 5: "SAP", 6: "GAP",
                   7: "STAP", 8: "RSAP", 9: "SGP",
                   10: "GGP", 11: "STGP", 12: "RSGP",
                   13: "RFS", 14: "SIO", 15: "GIO",
                   19: "CALC", 20: "COMP", 21: "JC",
                   22: "JA", 23: "CSUB", 24: "RSUB",
                   25: "EI", 26: "DI", 27: "WAIT",
                   28: "STOP", 30: "SCO", 31: "GCO",
                   32: "CCO", 33: "CALCX", 34: "AAP",
                   35: "AGP", 37: "VECT", 38: "RETI",
                   39: "ACO"
                   }

NUMBER_COMMANDS = dict([(v, k) for k, v in COMMAND_NUMBERS.items()])

INTERRUPT_VECTORS = {0: "Timer 0",
                     1: "Timer 1",
                     2: "Timer 2",
                     3: "Target position reached",
                     15: "stallGuard",
                     21: "Deviation",
                     27: "Left stop switch",
                     28: "Right stop switch",
                     39: "Input change 0",
                     40: "Input change 1",
                     255: "Global interrupts"}

CMD_MVP_TYPES = {'ABS': 0,
                 'REL': 1,
                 'COORD': 2}
CMD_RFS_TYPES = {'START': 0,
                 'STOP': 1,
                 'STATUS': 2}


def apard(name, prange, acc):
    return {"name": name,
            "range": prange,
            "access": acc}


TR_24s = [(-2 ** 23 + 1, 2 ** 23)]
TR_32u = [(0, 2 ** 32)]
TR_32s = [(-2 ** 31, 2 ** 31)]
TR_16u = [(0, 2 ** 16)]
TR_12s = [(-2 ** 11 + 1, 2 ** 11)]
TR_12u = [(0, 2 ** 12)]
TR_11u = [(0, 2 ** 11)]
TR_10u = [(0, 2 ** 10)]
TR_8u = [(0, 2 ** 8)]
TR_7s = [(-2 ** 6, 2 ** 6)]
TR_5u = [(0, 2 ** 5)]
TR_1u = [(0, 2 ** 1)]
TR_m3 = [(0, 3)]
TR_m4 = [(0, 4)]
TR_m9 = [(0, 9)]
TR_m12 = [(0, 14)]
TR_m14 = [(0, 14)]
TR_m16 = [(0, 16)]

TR_xCHP0 = [(-3, 13)]
TR_xCHP1 = [(0, 1), (2, 16)]
TR_xSE0 = [(1, 4)]
TR_xRFS0 = [(1, 137)]
TR_xRFS1 = [(0, 8388307)]
TR_xPWR0 = [(1, 2 ** 16)]
TR_xRND0 = [(0, 2 ** 31)]

T_R = 4
T_W = 2
T_E = 1
T_RW = T_R + T_W
T_RWE = T_RW + T_E

AXIS_PARAMETER = {0: ("target position", TR_24s, T_RW),
                  1: ("actual position", TR_24s, T_RW),
                  2: ("target speed", TR_12s, T_RW),
                  3: ("actual speed", TR_12s, T_RW),
                  4: ("max positioning speed", TR_11u, T_RWE),
                  5: ("max acceleration", TR_11u, T_RWE),
                  6: ("abs max current", TR_8u, T_RWE),
                  7: ("standby current", TR_8u, T_RWE),
                  8: ("target pos reached", TR_1u, T_R),
                  9: ("ref switch status", TR_1u, T_R),
                  10: ("right limit switch status", TR_1u, T_R),
                  11: ("left limit switch status", TR_1u, T_R),
                  12: ("right limit switch disable", TR_1u, T_RWE),
                  13: ("left limit switch disable", TR_1u, T_RWE),
                  130: ("minimum speed", TR_11u, T_RWE),
                  135: ("actual acceleration", TR_11u, T_R),
                  138: ("ramp mode", TR_m3, T_RWE),
                  140: ("microstep resolution", TR_m9, T_RWE),
                  141: ("ref switch tolerance", TR_12u, T_RW),
                  149: ("soft stop flag", TR_1u, T_RWE),
                  153: ("ramp divisor", TR_m14, T_RWE),
                  154: ("pulse divisor", TR_m14, T_RWE),
                  160: ("step interpolation enable", TR_1u, T_RW),
                  161: ("double step enable", TR_1u, T_RW),
                  162: ("chopper blank time", TR_m4, T_RW),
                  163: ("chopper mode", TR_1u, T_RW),
                  164: ("chopper hysteresis dec", TR_m4, T_RW),
                  165: ("chopper hysteresis end", TR_xCHP0, T_RW),
                  166: ("chopper hysteresis start", TR_m9, T_RW),
                  167: ("chopper off time", TR_xCHP1, T_RW),
                  168: ("smartEnergy min current", TR_1u, T_RW),
                  169: ("smartEnergy current downstep", TR_m4, T_RW),
                  170: ("smartEnergy hysteresis", TR_m16, T_RW),
                  171: ("smartEnergy current upstep", TR_xSE0, T_RW),
                  172: ("smartEnergy hysteresis start", TR_m16, T_RW),
                  173: ("stallGuard2 filter enable", TR_1u, T_RW),
                  174: ("stallGuard2 threshold", TR_7s, T_RW),
                  175: ("slope control high side", TR_m4, T_RW),
                  176: ("slope control low side", TR_m4, T_RW),
                  177: ("short protection disable", TR_1u, T_RW),
                  178: ("short detection timer", TR_m4, T_RW),
                  179: ("Vsense", TR_1u, T_RW),
                  180: ("smartEnergy actual current", TR_5u, T_RW),
                  181: ("stop on stall", TR_11u, T_RW),
                  182: ("smartEnergy threshold speed", TR_11u, T_RW),
                  183: ("smartEnergy slow run current", TR_8u, T_RW),
                  193: ("ref. search mode", TR_xRFS0, T_RWE),
                  194: ("ref. search speed", TR_11u, T_RWE),
                  195: ("ref. switch speed", TR_11u, T_RWE),
                  196: ("distance end switches", TR_xRFS1, T_R),
                  204: ("freewheeling", TR_16u, T_RWE),
                  206: ("actual load value", TR_10u, T_R),
                  208: ("TMC262 errorflags", TR_8u, T_R),
                  209: ("encoder pos", TR_24s, T_RW),
                  210: ("encoder prescaler", TR_16u, T_RWE),  # that one isnt really correct
                  212: ("encoder max deviation", TR_16u, T_RWE),
                  214: ("power down delay", TR_xPWR0, T_RWE)
                  }

# SINGLE_AXIS_PARAMETERS = [140]+range(160, 184)


GLOBAL_PARAMETER = {(0, 64): ("EEPROM magic", TR_8u, T_RWE),
                    (0, 65): ("RS485 baud rate", TR_m12, T_RWE),
                    (0, 66): ("serial address", TR_8u, T_RWE),
                    (0, 73): ("EEPROM lock flag", TR_1u, T_RWE),
                    (0, 75): ("telegram pause time", TR_8u, T_RWE),
                    (0, 76): ("serial host adress", TR_8u, T_RWE),
                    (0, 77): ("auto start mode", TR_1u, T_RWE),
                    (0, 81): ("TMCL code protect", TR_m4, T_RWE),
                    # Wrong type?? #(0, 84) : ("coordinate storage", TR_1u, T_RWE),
                    (0, 128): ("TMCL application status", TR_m3, T_R),
                    (0, 129): ("download mode", TR_1u, T_R),
                    (0, 130): ("TMCL program counter", TR_32u, T_R),
                    (0, 132): ("tick timer", TR_32u, T_RW),
                    # Wrong type?? #(0, 133) : ("random number", TR_xRND0, T_R),
                    (3, 0): ("Timer0 period", TR_32u, T_RWE),
                    (3, 1): ("Timer1 period", TR_32u, T_RWE),
                    (3, 2): ("Timer2 period", TR_32u, T_RWE),
                    (3, 39): ("Input0 edge type", TR_m4, T_RWE),
                    (3, 40): ("Input0 edge type", TR_m4, T_RWE)
                    }
# add general purpose registers
for b, p, a in zip([2] * 256, range(256), ([T_RWE] * 56) + ([T_RW] * 200)):
    GLOBAL_PARAMETER[(2, p)] = ("general purpose reg#{0:0>3d}".format(p), TR_32s, a)


class TMCLDevice(object):

    def __init__(self, port="/dev/ttyACM0", debug=False):
        self._port = port
        self._debug = debug
        self.serial = serial.Serial(port)

    def stop(self):
        """Close serial."""
        self.serial.close()

    def _query(self, request):
        """Encode and send a query. Receive, decode, and return reply"""
        # Insert inside encode request command function a way to check the value ranges
        req = encode_request_command(*request)
        req = list(map(ord, req))
        if self._debug:
            print(("send to TMCL: ", self._hex_string(req), decode_request_command(req)))
        self.serial.write(req)
        resp = decode_reply_command(self.serial.read(9))
        if self._debug:
            tmp = list(resp.values())[:-1]
            tmp = encode_reply_command(*tmp)
            print(("got from TMCL:", self._hex_string(tmp), resp))
        return resp['status'], resp['value']

    def _hex_string(self, cmd):
        """Convert encoded command string to human-readable string of hex values"""
        temp = None
        # Quickfix
        if (type(cmd[0]) is str):
            temp = [ord(i) for i in cmd]
        elif (type(cmd[0]) is int):
            temp = [i for i in cmd]

        s = ['{:x}'.format(i).rjust(2) for i in temp]
        return "[" + ", ".join(s) + "]"

    def _pn_checkrange(self, parameter_number, value, prefix):
        pn = parameter_number
        v = int(value)
        DICT = AXIS_PARAMETER if type(pn) == int else GLOBAL_PARAMETER
        if not pn in DICT.keys():
            raise TMCLError(prefix + "parameter number not valid")
        name, ranges, _ = DICT[parameter_number]
        NOTINRANGE = False
        for (l, h) in ranges:
            if not (l <= v < h):
                NOTINRANGE = True
        if NOTINRANGE:
            raise TMCLError(prefix + "parameter " + name + " needs " + "+".join(
                ["range(" + str(l) + ", " + str(h) + ")" for l, h in ranges]))
        return pn, v

    def ror(self, motor_number, velocity):
        """
        tmcl_ror(motor_number, velocity) --> None

        The motor will be instructed to rotate with a specified velocity
        in right direction (increasing the position counter).

        TMCL-Mnemonic: ROR <motor number>, <velocity>
        """
        cn = NUMBER_COMMANDS['ROR']
        mn = int(motor_number)
        v = int(velocity)
        if not 0 <= mn <= 2:
            raise TMCLError("ROR: motor_number not in range(3)")
        if not 0 <= v <= 2047:
            raise TMCLError("ROR: velocity not in range(2048)")
        status, value = self._query((0x01, cn, 0x00, mn, v))
        if status != STAT_OK:
            raise TMCLError("ROR: got status " + STATUS_CODES[status])
        return None

    def rol(self, motor_number, velocity):
        """
        tmcl_rol(motor_number, velocity) --> None

        With this command the motor will be instructed to rotate with a
        specified velocity (opposite direction compared to tmcl_rol,
        decreasing the position counter).

        TMCL-Mnemonic: ROL <motor number>, <velocity>
        """
        cn = NUMBER_COMMANDS['ROL']
        mn = int(motor_number)
        v = int(velocity)
        if not 0 <= mn <= 2:
            raise TMCLError("ROL: motor_number not in range(3)")
        if not 0 <= v <= 2047:
            raise TMCLError("ROL: velocity not in range(2048)")
        status, value = self._query((0x01, cn, 0x00, mn, v))
        if status != STAT_OK:
            raise TMCLError("ROL: got status " + STATUS_CODES[status])
        return None

    def mst(self, motor_number):
        """
        tmcl_mst(motor_number) --> None

        The motor will be instructed to stop.

        TMCL-Mnemonic: MST <motor number>
        """
        cn = NUMBER_COMMANDS['MST']
        mn = int(motor_number)
        if not 0 <= mn <= 2:
            raise TMCLError("MST: motor_number not in range(3)")
        status, value = self._query((0x01, cn, 0x00, mn, 0x00))
        if status != STAT_OK:
            raise TMCLError("MST: got status " + STATUS_CODES[status])
        return None

    def mvp(self, motor_number, cmdtype, value):
        """
        tmcl_mvp(motor_number, type, value) --> None

        The motor will be instructed to move to a specified relative or
        absolute position or a pre-programmed coordinate. It will use
        the acceleration/deceleration ramp and the positioning speed
        programmed into the unit. This command is non-blocking: that is,
        a reply will be sent immediately after command interpretation
        and initialization of the motion controller. Further commands
        may follow without waiting for the motor reaching its end
        position. The maximum velocity and acceleration are defined by
        axis parameters #4 and #5.

        Three operation types are available:
            * Moving to an absolute position in the range from
              -8388608 to +8388607 (-223 to+223-1).
            * Starting a relative movement by means of an offset to the
              actual position. In this case, the new resulting position
              value must not exceed the above mentioned limits, too.
            * Moving the motor to a (previously stored) coordinate
              (refer to SCO for details).

        TMCL-Mnemonic: MVP <ABS|REL|COORD>, <motor number>,
                           <position|offset|coordinate number>
        """
        cn = NUMBER_COMMANDS['MVP']
        mn = int(motor_number)
        t = str(cmdtype)
        v = int(value)
        if not 0 <= mn <= 2:
            raise TMCLError("MVP: motor_number not in range(3)")
        if t not in CMD_MVP_TYPES.keys():
            raise TMCLError("MVP: type not in ['ABS', 'REL', 'COORD']")
        if t == 'ABS' and not -2 ** 23 <= v <= 2 ** 23:
            raise TMCLError("MVP: ABS: value not in range(-2**23,2**23)")
        # pass 'REL' because we dont know the current pos here
        if t == 'COORD' and not 0 <= v <= 20:
            raise TMCLError("MVP: COORD: value not in range(21)")
        t = CMD_MVP_TYPES[t] % (1 << 8)
        status, value = self._query((0x01, cn, t, mn, v))
        if status != STAT_OK:
            raise TMCLError("MVP: got status " + STATUS_CODES[status])
        return None

    def rfs(self, motor_number, cmdtype):
        """
        tmcl_rfs(motor_number, cmdtype) --> int

        The TMCM-1110 has a built-in reference search algorithm which
        can be used. The reference search algorithm provides switching
        point calibration and three switch modes. The status of the
        reference search can also be queried to see if it has already
        finished. (In a TMCLTM program it is better to use the WAIT
        command to wait for the end of a reference search.) Please see
        the appropriate parameters in the axis parameter table to
        configure the reference search algorithm to meet your needs
        (chapter 6). The reference search can be started, stopped, and
        the actual status of the reference search can be checked.

        if cmdtype in ['START', 'STOP']:
            return 0
        if cmdtype == 'STATUS':
            return 0 if "ref-search is active" else "other values"

        TMCL-Mnemonic: RFS <START|STOP|STATUS>, <motor number>
        """
        cn = NUMBER_COMMANDS['RFS']
        mn = int(motor_number)
        t = str(cmdtype)
        if not 0 <= mn <= 2:
            raise TMCLError("RFS: motor_number not in range(3)")
        if t not in CMD_RFS_TYPES.keys():
            raise TMCLError("RFS: type not in ['START', 'STOP', 'STATUS']")
        t = CMD_RFS_TYPES[t] % (1 << 8)
        status, value = self._query((0x01, cn, t, mn, 0x0000))
        if status != STAT_OK:
            raise TMCLError("RFS: got status " + STATUS_CODES[status])
        return value if t == CMD_RFS_TYPES['STATUS'] else 0

    def cco(self, motor_number, coordinate_number):
        """
        tmcl_cco(motor_number, coordinate_number) --> None

        The actual position of the axis is copied to the selected
        coordinate variable. Depending on the global parameter 84, the
        coordinates are only stored in RAM or also stored in the EEPROM
        and copied back on startup (with the default setting the
        coordinates are stored in RAM only). Please see the SCO and GCO
        commands on how to copy coordinates between RAM and EEPROM.
        Note, that the coordinate number 0 is always stored in RAM only.

        TMCL-Mnemonic: CCO <coordinate number>, <motor number>
        """
        cn = NUMBER_COMMANDS['CCO']
        mn = int(motor_number)
        coord_n = int(coordinate_number)
        if not 0 <= mn <= 2:
            raise TMCLError("CCO: motor_number not in range(3)")
        if not 0 <= coord_n <= 20:
            raise TMCLError("CCO: coordinate_number not in range(21)")
        status, value = self._query((0x01, cn, coord_n, mn, 0x0000))
        if status != STAT_OK:
            raise TMCLError("CCO: got status " + STATUS_CODES[status])
        return None

    def sco(self, motor_number, coordinate_number, position):
        """
        tmcl_sco(self, motor_number, coordinate_number, position) --> None

        Up to 20 position values (coordinates) can be stored for every
        axis for use with the MVP COORD command. This command sets a
        coordinate to a specified value. Depending on the global
        parameter 84, the coordinates are only stored in RAM or also
        stored in the EEPROM and copied back on startup (with the
        default setting the coordinates are stored in RAM only).
        Please note that the coordinate number 0 is always stored in
        RAM only.

        TMCL-Mnemonic: SCO <coordinate number>, <motor number>, <position>
        """
        cn = NUMBER_COMMANDS['SCO']
        mn = int(motor_number)
        coord_n = int(coordinate_number)
        pos = int(position)
        if not 0 <= coord_n <= 20:
            raise TMCLError("SCO: coordinate_number not in range(21)")
        if not -2 ** 23 <= pos <= 2 ** 23:
            raise TMCLError("SCO: position not in range(-2**23,2**23)")
        if not 0 <= mn <= 2:
            raise TMCLError("SCO: motor_number not in range(3)")
        elif not (mn == 0xFF and pos == 0):
            raise TMCLError("SCO: special function needs pos == 0")
        status, value = self._query((0x01, cn, coord_n, mn, pos))
        if status != STAT_OK:
            raise TMCLError("SCO: got status " + STATUS_CODES[status])
        return None

    def gco(self, motor_number, coordinate_number):
        """
        tmcl_gco(self, motor_number, coordinate_number) --> int

        This command makes possible to read out a previously stored
        coordinate. In standalone mode the requested value is copied to
        the accumulator register for further processing purposes such
        as conditioned jumps. In direct mode, the value is only output
        in the value field of the reply, without affecting the
        accumulator. Depending on the global parameter 84, the
        coordinates are only stored in RAM or also stored in the EEPROM
        and copied back on startup (with the default setting the
        coordinates are stored in RAM, only).
        Please note that the coordinate number 0 is always stored in
        RAM, only.

        TMCL-Mnemonic: GCO <coordinate number>, <motor number>
        """
        pos = 0
        cn = NUMBER_COMMANDS['GCO']
        mn = int(motor_number)
        coord_n = int(coordinate_number)
        if not 0 <= coord_n <= 20:
            raise TMCLError("GCO: coordinate_number not in range(21)")
        if not (0 <= mn <= 2 or mn == 0xFF):
            raise TMCLError("GCO: motor_number not in range(3)")
        elif not (mn == 0xFF and pos == 0):
            raise TMCLError("GCO: special function needs pos == 0")
        status, value = self._query((0x01, cn, coord_n, mn, pos))
        if status != STAT_OK:
            raise TMCLError("GCO: got status " + STATUS_CODES[status])
        return value

    def sio(self, port_number, state):
        """
        tmcl_sio(output_number, state) --> None

        This command sets the status of the general digital output
        either to low (0) or to high (1).

        TMCL-Mnemonic: SIO <port number>, <bank number>, <value>
        """
        cn = NUMBER_COMMANDS['SIO']
        outp = int(port_number)
        s = bool(state)
        if not 0 <= outp <= 4:
            raise TMCLError("SIO: output_number not in range(5)")
        status, value = self._query((0x01, cn, outp, 0x02, s))
        if status != STAT_OK:
            raise TMCLError("SIO: got status " + STATUS_CODES[status])
        return None

    def gio(self, port_number, bank_number):
        """
        tmcl_gio(port_number, bank_number) --> int

        With this command the status of the two available general
        purpose inputs of the module can be read out. The function
        reads a digital or analogue input port. Digital lines will read
        0 and 1, while the ADC channels deliver their 12 bit result in
        the range of 0... 4095. In direct mode the value is only output
        in the value field of the reply, without affecting the accumulator.
        The actual status of a digital output line can also be read.

        TMCL-Mnemonic: GIO <port number>, <bank number>
        """
        cn = NUMBER_COMMANDS['GIO']
        outp = int(port_number)
        bank = int(bank_number)
        if bank == 0:
            if not (0 <= outp <= 3):
                raise TMCLError("GIO: output_number not in range(4) @ bank0")
        elif bank == 1:
            if not (0 <= outp <= 2):
                raise TMCLError("GIO: output_number not in range(3) @ bank1")
        elif bank == 2:
            if not (0 <= outp <= 4):
                raise TMCLError("GIO: output_number not in range(5) @ bank2")
        else:
            raise TMCLError("GIO: bank_number not in range(3)")
        status, value = self._query((0x01, cn, outp, bank, 0x0000))
        if status != STAT_OK:
            raise TMCLError("GIO: got status " + STATUS_CODES[status])
        return value

    def sap(self, motor_number, parameter_number, value):
        """
        tmcl_sap(motor_number, parameter_number, value) --> None

        Most of the motion control parameters of the module can be
        specified with the SAP command. The settings will be stored in
        SRAM and therefore are volatile. That is, information will be
        lost after power off. Please use command STAP (store axis
        parameter) in order to store any setting permanently.

        TMCL-Mnemonic: SAP <parameter number>, <motor number>, <value>
        """
        cn = NUMBER_COMMANDS['SAP']
        mn = int(motor_number)
        if not 0 <= mn <= 2:
            raise TMCLError("SAP: motor_number not in range(3)")
        pn, v = self._pn_checkrange(parameter_number, value, "SAP: ")
        status, value = self._query((0x01, cn, pn, mn, v))
        if status != STAT_OK:
            raise TMCLError("SAP: got status " + STATUS_CODES[status])
        return None

    def gap(self, motor_number, parameter_number):
        """
        tmcl_gap(self, motor_number, parameter_number) --> int

        Most parameters of the TMCM-1110 can be adjusted individually
        for the axis. With this parameter they can be read out. In
        standalone mode the requested value is also transferred to the
        accumulator register for further processing purposes (such as
        conditioned jumps). In direct mode the value read is only
        output in the value field of the reply (without affecting the
        accumulator).

        TMCL-Mnemonic: GAP <parameter number>, <motor number>
        """
        cn = NUMBER_COMMANDS['GAP']
        mn = int(motor_number)
        pn = int(parameter_number)
        if not 0 <= mn <= 2:
            raise TMCLError("GAP: motor_number not in range(3)")
        if pn not in AXIS_PARAMETER.keys():
            raise TMCLError("GAP: parameter number not valid")
        status, value = self._query((0x01, cn, pn, mn, 0x0000))
        if status != STAT_OK:
            raise TMCLError("GAP: got status " + STATUS_CODES[status] + ", while querying " + str(pn))
        return value

    def sgp(self, bank_number, parameter_number, value):
        """
        tmcl_sgp(self, bank_number, parameter_number, value) --> None

        Most of the module specific parameters not directly related to
        motion control can be specified and the TMCLTM user variables
        can be changed. Global parameters are related to the host
        interface, peripherals or other application specific variables.
        The different groups of these parameters are organized in banks
        to allow a larger total number for future products. Currently,
        bank 0 and bank 1 are used for global parameters. Bank 2 is
        used for user variables and bank 3 is used for interrupt
        configuration.

        All module settings will automatically be stored non-volatile
        (internal EEPROM of the processor). The TMCLTM user variables
        will not be stored in the EEPROM automatically, but this can
        be done by using STGP commands.

        TMCL-Mnemonic: SGP <parameter number>, <bank number>, <value>
        """
        cn = NUMBER_COMMANDS['SGP']
        bn = int(bank_number)
        pn = int(parameter_number)
        v = int(value)
        if not 0 <= bn <= 3:
            raise TMCLError("SGP: bank_number not in range(4)")
        pn, v = self._pn_checkrange((bn, pn), v, "SGP: ")
        status, value = self._query((0x01, cn, pn, bn, v))
        if status != STAT_OK:
            raise TMCLError("SGP: got status " + STATUS_CODES[status])
        return None

    def ggp(self, bank_number, parameter_number):
        """
        tmcl_ggp(self, bank_number, parameter_number) --> int

        All global parameters can be read with this function. Global
        parameters are related to the host interface, peripherals or
        application specific variables. The different groups of these
        parameters are organized in banks to allow a larger total
        number for future products. Currently, bank 0 and bank 1 are
        used for global parameters. Bank 2 is used for user variables
        and bank 3 is used for interrupt configuration. Internal
        function: the parameter is read out of the correct position
        in the appropriate device. The parameter format is converted
        adding leading zeros (or ones for negative values).

        TMCL-Mnemonic: GGP <parameter number>, <bank number>
        """
        cn = NUMBER_COMMANDS['GGP']
        bn = int(bank_number)
        pn = int(parameter_number)
        if not 0 <= bn <= 3:
            raise TMCLError("GGP: bank_number not in range(4)")
        if not (bn, pn) in GLOBAL_PARAMETER.keys():
            raise TMCLError("GGP: parameter number not valid")
        status, value = self._query((0x01, cn, pn, bn, 0x0000))
        if status != STAT_OK:
            raise TMCLError("GGP: got status " + STATUS_CODES[status])
        return value

    def stap(self, motor_number, parameter_number):
        """
        tmcl_stap(self, motor_number, parameter_number) --> None

        An axis parameter previously set with a Set Axis Parameter
        command (SAP) will be stored permanent. Most parameters are
        automatically restored after power up.

        TMCL-Mnemonic: STAP <parameter number>, <motor number>
        """
        cn = NUMBER_COMMANDS['STAP']
        mn = int(motor_number)
        if not 0 <= mn <= 2:
            raise TMCLError("STAP: motor_number not in range(3)")
        pn = int(parameter_number)
        if not pn in AXIS_PARAMETER.keys():
            raise TMCLError("STAP: parameter number not valid")
        status, value = self._query((0x01, cn, pn, mn, 0x0000))
        if status != STAT_OK:
            raise TMCLError("STAP: got status " + STATUS_CODES[status])
        return None

    def rsap(self):
        raise NotImplementedError("yet!")

    def stgp(self):
        raise NotImplementedError("yet!")

    def rsgp(self):
        raise NotImplementedError("yet!")
