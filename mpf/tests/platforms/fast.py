"""FAST Pinball mock hardware platform. In this module:

MockFastSerial
MockFastNetNeuron
MockFastExp
MockFastRgb
MockFastNetNano
MockFastSeg
MockFastDmd
"""

from mpf.tests.loop import MockSerial

class MockFastSerial(MockSerial):

    PRINT_FSP_TRAFFIC = True

    def __init__(self, test_fast_base):
        super().__init__()
        self.test_fast_base = test_fast_base
        self.type = None
        self.queue = []
        self.msg_history = list()  # list of commands received, e.g. ['ID:', 'ID@88:', 'ID@89:', 'EA:880', 'RD:0200ffffff121212']
        self.expected_commands = dict()  # popped when called, verify empty at end of test
        self.autorespond_commands = dict()  # can be called multiple times, never popped
        self.port = None

    def read(self, length):
        """ Reads the message from receive queue"""
        del length
        if not self.queue:
            return

        msg = self.queue.pop()
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

        if self.PRINT_FSP_TRAFFIC:
            print(f'{self.type} >>> {cmd}')

        self.msg_history.append(cmd)

        # Order of precedence is key here. We want autoresponses to be last so they can be overridden
        # via custom responses or expected commands on a per-test basis.

        rsp = self.process_msg(cmd)

        if rsp:
            if self.PRINT_FSP_TRAFFIC:
                print(f'{self.type} <<< {rsp}')
                self.queue.append(rsp)
            return msg_len

        if cmd in self.expected_commands:
            if self.expected_commands[cmd]:
                self.queue.append(self.expected_commands[cmd])
                if self.PRINT_FSP_TRAFFIC:
                    print(f'{self.type} <<< {self.expected_commands[cmd]}')
            del self.expected_commands[cmd]
            return msg_len

        if cmd in self.autorespond_commands:
            self.queue.append(self.autorespond_commands[cmd])
            if self.PRINT_FSP_TRAFFIC:
                print(f'{self.type} <<< {self.autorespond_commands[cmd]}')
            return msg_len

        raise Exception(f"Unexpected command for {self.type}: {cmd}")

    def _process_binary_msg(self, msg):
        # The first three chars are the command (XX:), the rest is the binary payload
        return f'{msg[:3].decode()}{msg[3:].hex()}'


class MockFastNetNeuron(MockFastSerial):
    def __init__(self, test_fast_base):
        super().__init__(test_fast_base)
        self.type = "NETv2"
        self.port = 'com3'

        self.autorespond_commands = {
            'WD:1' : 'WD:P',
            'WD:3E8': 'WD:P',
            'SA:':'SA:0E,2900000000000000000000000000',
            'CH:2000,FF':'CH:P',
            'ID:': 'ID:NET FP-CPU-2000  02.13',
            'BR:': '\r\r!B:00\r..!B:02\r.',
            }

        self.attached_boards = dict()
        self.msg_history = list()

    def process_msg(self, cmd):
        if cmd == (' ' * 256 * 4):
            return "XX:F"

        return False


class MockFastExp(MockFastSerial):
    def __init__(self, test_fast_base):
        super().__init__(test_fast_base)
        self.type = 'EXP'
        self.port = 'com4'
        self.leds = dict()
        self.led_map = dict()  # LED number to name index, e.g. 88000: "led1", 88121: "led5"

    def process_msg(self, cmd):
        # returns True if the msg was fully processed, False if it was not

        cmd, payload = cmd.split(":", 1)
        cmd, temp_active = cmd.split("@", 1)

        if cmd == "ID":
            if not temp_active:  # no ID has been set, so lowest address will respond
                return "ID:EXP FP-EXP-2000 0.11"

            if temp_active == '48':  # Neuron
                return "ID:EXP FP-EXP-2000 0.11"

            elif temp_active in ["B4", "B5", "B6", "B7"]:  # 71
                return "ID:EXP FP-EXP-0071  0.11"

            elif temp_active in ["84", "85", "86", "87"]:  # 81
                return "ID:EXP FP-EXP-0081  0.12"

            elif temp_active in ["88", "89", "8A", "8B"]:  # 91
                return "ID:EXP FP-EXP-0091  0.11"

            # Breakouts
            elif temp_active == "480":  # Neuron
                return "ID:LED FP-BRK-0001  0.8"

            elif temp_active == '481':  # Neuron
                return "ID:BRK FP-PWR-0007  0.8"

            elif temp_active == '482':  # Neuron
                return "ID:BRK FP-BRK-0116  0.8"

            elif temp_active in ["B40", "B50", "B60", "B70"]:  # 71
                return "ID:BRK FP-EXP-0071  0.11"

            elif temp_active in ["840", "850", "860", "870",
                                 "841", "851", "861", "871"]:  # 81
                return "ID:BRK FP-EXP-0081  0.12"

            elif temp_active in ["880", "890", "8A0", "8B0"]:  # 91
                return "ID:BRK FP-EXP-0091  0.11"

            elif temp_active in ["881", "892"]:  # 091
                return "ID:BRK FP-BRK-0001  0.8"

            elif temp_active in ["882"]:  # 091
                return "ID:BRK FP-DRV-0800  0.0"

            assert False, f"Unexpected ID request for {temp_active}"

        elif cmd == "BR":
            # turn off all the LEDs on that board
            for led_number, led_name in self.led_map.items():
                if led_number.startswith(temp_active):
                    self.leds[led_name] = "000000"

            return "BR:P"

        elif cmd == "RD":
            # Update LED colors
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

class MockFastRgb(MockFastSerial):
    def __init__(self, test_fast_base):
        super().__init__(test_fast_base)
        self.type = 'RGB'
        self.port = 'com5'

        self.autorespond_commands = {
            'ID:': 'ID:RGB FP-CPU-002-2 00.89',
            }

        self.leds = dict()

    def process_msg(self, cmd):
        if cmd[:3] == "RS:":
            remaining = cmd[3:]
            while True:
                self.leds[remaining[0:2]] = remaining[2:8]
                remaining = remaining[9:]

                if not remaining:
                    break

            return "RX:P"


class MockFastNetNano(MockFastSerial):
    def __init__(self, test_fast_base):
        super().__init__(test_fast_base)
        self.type = "NETv1"
        self.port = 'com4'

        self.autorespond_commands = {
            'WD:1' : 'WD:P',
            'WD:3E8': 'WD:P',
            "SA:": "SA:01,00,09,050000000000000000",
            'ID:': 'ID:NET FP-CPU-002-2  01.05',
            }

        self.attached_boards = dict()
        self.msg_history = list()

    def process_msg(self, cmd):
        if cmd == (' ' * 256 * 4):
            return "XX:F"
        return False

class MockFastSeg(MockFastSerial):
    def __init__(self, test_fast_base):
        super().__init__(test_fast_base)
        self.type = "SEG"
        self.port = "com7"

        self.autorespond_commands = {
            'ID:': 'ID:SEG FP-CPU-002-2 00.10',
            }

class MockFastDmd(MockFastSerial):
    def __init__(self, test_fast_base):
        super().__init__(test_fast_base)
        self.type = "DMD"
        self.port = 'com8'

        self.autorespond_commands = {
            'ID:': 'ID:DMD FP-CPU-002-2 00.88',
            }
