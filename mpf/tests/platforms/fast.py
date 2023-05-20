"""FAST Pinball mock hardware platform.

In this module:

MockFastSerial
MockFastNetNeuron
MockFastExp
MockFastDmd
MockFastRgb
MockFastSeg



"""

from mpf.tests.loop import MockSerial

class MockFastSerial(MockSerial):

    def __init__(self):
        super().__init__()
        self.type = None
        self.queue = []
        self.msg_history = list()  # list of commands received, e.g. ['ID:', 'ID@88:', 'ID@89:', 'EA:880', 'RD:0200ffffff121212']
        self.expected_commands = dict()  # popped when called, verify empty at end of test
        self.autorespond_commands = dict()  # can be called multiple times, never popped

    def read(self, length):
        """ Reads the message from receive queue"""
        del length
        if not self.queue:
            return

        msg = self.queue.pop()
        # print(f'{self.type} <<< {msg}')
        msg = (msg + '\r').encode()
        return msg

    def read_ready(self):
        return bool(len(self.queue) > 0)

    def write_ready(self):
        return True

    def process_msg(self, msg):
        """Override this to apply further processing to a message.
        Return True if processed and complete, False if not."""
        return False

    def write(self, msg):
        """Write message out to the serial port."""
        parts = msg.split(b'\r')
        for part in parts:
            if part == b'':
                continue
            self._simulate_board_response(part)

        return len(msg)

    def _simulate_board_response(self, msg):
        # handles the processing of outgoing messages
        msg_len = len(msg)
        try:
            cmd = msg.decode()
        except UnicodeDecodeError:
            cmd = self._process_binary_msg(msg)

        # print(f'{self.type} >>> {cmd}')

        self.msg_history.append(cmd)

        if cmd in self.autorespond_commands:
            self.queue.append(self.autorespond_commands[cmd])
            return msg_len

        if self.process_msg(cmd):
            return msg_len

        if cmd in self.expected_commands:
            if self.expected_commands[cmd]:
                self.queue.append(self.expected_commands[cmd])
            del self.expected_commands[cmd]
            return msg_len
        else:
            raise Exception("Unexpected command for " + self.type + ": " + str(cmd))

    def _process_binary_msg(self, msg):
        # The first three chars are the command (XX:), the rest is the binary payload
        return f'{msg[:3].decode()}{msg[3:].hex()}'


class MockFastNetNeuron(MockFastSerial):  # TODO change this to just neuron
    def __init__(self):
        super().__init__()
        self.type = "NET"
        # self.expected_commands = {
        #     ' ' * 1024: 'XX:F',
        #     'CH:2000,FF':'CH:P',
        #     'SA:':'SA:09,050000000000000000',
        #     'ID:': 'NET FP-CPU-2000  02.06',
        # }

        self.autorespond_commands = {
            'WD:1' : 'WD:P',
            'WD:3E8': 'WD:P',
            'SA:':'SA:09,050000000000000000',
            'CH:2000,FF':'CH:P',
            'ID:': 'ID:NET FP-CPU-2000  02.06',
            'BR:': '\r\r!B:00\r..!B:02\r.',
            }

        self.attached_boards = {
            'NN:00': 'NN:00,FP-I/O-3208-3   ,01.09,08,20,00,00,00,00,00,00',     # 3208 board
            'NN:01': 'NN:01,FP-I/O-0804-3   ,01.09,04,08,00,00,00,00,00,00',     # 0804 board
            'NN:02': 'NN:02,FP-I/O-1616-3   ,01.09,10,10,00,00,00,00,00,00',     # 1616 board
            'NN:03': 'NN:03,FP-I/O-1616-3   ,01.09,10,10,00,00,00,00,00,00',     # 1616 board
            'NN:04': 'NN:04,FP-I/O-0024-3   ,01.10,08,18,00,00,00,00,00,00',     # Cab I/O board
        }
        self.msg_history = list()

    def process_msg(self, cmd):
        if cmd == (' ' * 256 * 4):
            self.queue.append("XX:F")  # TODO move to Net subclass?
            return True

        return False


class MockFastExp(MockFastSerial):
    def __init__(self, test_fast_base):
        super().__init__()
        self.test_fast_base = test_fast_base
        self.type = 'EXP'
        self.active_board = None
        self.leds = dict()
        self.led_map = dict()  # LED number to name index, e.g. 88000: "led1", 88121: "led5"

    def process_msg(self, cmd):
        # returns True if the msg was fully processed, False if it was not

        cmd, payload = cmd.split(":", 1)

        if '@' in cmd:
            cmd, temp_active = cmd.split("@", 1)

        elif cmd == "EA":
            temp_active = self.active_board = payload.upper()
            return True

        else:
            temp_active = self.active_board

        if cmd == "ID":

            if temp_active in ["88", "89", "8A", "8B"]:  # 091
                self.queue.append("ID:EXP FP-EXP-0091  0.8")

            elif temp_active in ["480", "880", "881", "890", "893"]:  # 091
                self.queue.append("ID:LED FP-BRK-0001  0.0")

            elif temp_active in ["882"]:  # 091
                self.queue.append("ID:BRK FP-DRV-0800  0.0")

            elif temp_active in ["B4", "B5", "B6", "B7"]:  # 71
                self.queue.append("ID:EXP FP-EXP-0071  0.8")

            elif temp_active == 'B40':  # Neuron
                self.queue.append("ID:BRK FP-EXP-0071  0.0")

            elif temp_active in ["84", "85", "86", "87"]:  # 71
                self.queue.append("ID:EXP FP-EXP-0081  0.8")

            elif temp_active == '840':  # Neuron
                self.queue.append("ID:BRK FP-EXP-0081  0.0")

            elif temp_active == '48':  # Neuron
                self.queue.append("ID:EXP FP-EXP-2000 0.8")

            elif temp_active == '481':  # Neuron
                self.queue.append("ID:LED FP-PWR-0007  0.8")

            elif temp_active == '482':  # Neuron
                self.queue.append("ID:BRK FP-BRK-0116  0.8")

            if not temp_active:  # no ID has been set, so lowest address will respond
                self.queue.append("ID:EXP FP-EXP-2000 0.8")

            return True

        elif cmd == "BR":
            # turn off all the LEDs on that board
            for led_number, led_name in self.led_map.items():
                if led_number.startswith(temp_active):
                    self.leds[led_name] = "000000"

            self.queue.append("BR:P")
            return True

        elif cmd == "RD":
            # RD:<COUNT>{<INDEX><R><G><B>...}
            # 88120

            self.test_fast_base.assertTrue(self.active_board, "Received RD: command with no active expansion board set")

            if not self.led_map:
                for name, led in self.test_fast_base.machine.lights.items():
                    led_number = led.hw_drivers['red'][0].number.split('-')[0]  # 88000
                    self.led_map[led_number] = name

            payload = payload.upper()
            count = int(payload[:2], 16)
            color_data = payload[2:]

            assert len(color_data) == count * 8

            # update our record of the LED colors
            for i in range(count):
                color = color_data[i * 8 + 2:i * 8 + 8]
                led_number = f'{self.active_board}{color_data[i * 8:i * 8 + 2]}'

                self.leds[self.led_map[led_number]] = color

            return True

        return False


class MockFastDmd(MockFastSerial):
    def __init__(self):
        super().__init__()
        self.type = "DMD"

    def _simulate_board_response(self, msg):
        msg_len = len(msg)
        if msg == (b' ' * 256 * 4):
            return msg_len

        cmd = msg

        if cmd[:3] == "WD:":
            self.queue.append("WD:P")
            return msg_len

        if cmd in self.autorespond_commands:
            self.queue.append(cmd[:3] + "P")
            return msg_len

        if cmd in self.expected_commands:
            if self.expected_commands[cmd]:
                self.queue.append(self.expected_commands[cmd])
            del self.expected_commands[cmd]
            return msg_len
        else:
            raise Exception(self.type + ": " + str(cmd))


class MockFastRgb(MockFastSerial):
    def __init__(self):
        super().__init__()
        self.type = "RGB"

        self.autorespond_commands = {
            'L1:23,FF': 'L1:P',
            'RF:0': 'RF:P',
            'RF:00': 'RF:P',
            'RA:000000': 'RA:P',
        }

        self.leds = {}

    def process_msg(self, cmd):
        if cmd[:3] == "RS:":
            remaining = cmd[3:]
            while True:
                self.leds[remaining[0:2]] = remaining[2:8]
                remaining = remaining[9:]

                if not remaining:
                    break

            self.queue.append("RX:P")
            return True


class MockFastSeg(MockFastSerial):
    def __init__(self):
        super().__init__()
        self.type = "SEG"