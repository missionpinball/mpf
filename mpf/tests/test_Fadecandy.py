from mock import MagicMock
import json

from mpf.core.rgb_color import RGBColor
from mpf.platforms import openpixel
from mpf.tests.MpfTestCase import MpfTestCase


class TestOpenpixel(MpfTestCase):
    def getConfigFile(self):
        return 'fadecandy.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/openpixel/'

    def get_platform(self):
        return 'fadecandy'

    def setUp(self):
        self._messages = []
        self._opcthread = openpixel.OPCThread
        openpixel.OPCThread = MagicMock()
        self._send = openpixel.OpenPixelClient.send
        openpixel.OpenPixelClient.send = self._send_mock
        super().setUp()
        color_correct = self._messages.pop(0)
        color_correct_binary = 'b\'\\x00\\xff\\x00Z\\x00\\x01\\x00\\x01\''
        self.assertEqual(color_correct[0:len(color_correct_binary)], color_correct_binary)
        correction = {"linearSlope": 1.0, "linearCutoff": 0.0, "gamma": 2.5, "whitepoint": [1.0, 1.0, 1.0]}
        self.assertEqual(json.loads(color_correct[len(color_correct_binary):]), correction)

        firmware = self._messages.pop(0)
        self.assertEqual(firmware, b'\x00\xff\x00\x05\x00\x01\x00\x02\x00')

        self.assertOpenPixelLedsSent({}, {})

    def tearDown(self):
        super().tearDown()
        openpixel.OPCThread = self._opcthread
        openpixel.OpenPixelClient.send = self._send

    def _build_message(self, channel, leds):
        out = chr(channel) + chr(0) + chr(1) + chr(44)
        for i in range(0, 100):
            if i in leds:
                out += chr(leds[i][0]) + chr(leds[i][1]) + chr(leds[i][2])
            else:
                out += chr(0) + chr(0) + chr(0)

        return out

    def _send_mock(self, message):
        self._messages.append(message)

    def assertOpenPixelLedsSent(self, leds1, leds2):
        bank1 = self._build_message(0, leds1)
        bank2 = self._build_message(1, leds2)
        found1 = False
        found2 = False
        for message in self._messages:
            if not (message == bank1 or message == bank2):
                print(":".join("{:02x}".format(ord(c)) for c in message))
                print(":".join("{:02x}".format(ord(c)) for c in bank1))
                print(":".join("{:02x}".format(ord(c)) for c in bank2))
                raise AssertionError("Invalid Message")
            if message == bank1:
                found1 = True
            else:
                found2 = True

        self.assertTrue(found1)
        self.assertTrue(found2)
        self._messages = []

    def test_led_color(self):
        # test led on channel 0. position 99
        self.machine.leds.test_led.on()
        self.machine_run()
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, {})

        # test led 20 ond channel 0
        self.machine.leds.test_led2.color(RGBColor((255, 0, 0)))
        self.machine_run()
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (255, 255, 255)}, {})

        self.machine.leds.test_led.off()
        self.machine_run()
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (0, 0, 0)}, {})
        self._messages = []

        # test led color
        self.machine.leds.test_led.color(RGBColor((2, 23, 42)))
        self.machine_run()
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (2, 23, 42)}, {})

        # test led on channel 1
        self.machine.leds.test_led3.on()
        self.machine_run()
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (2, 23, 42)}, {99: (255, 255, 255)})
