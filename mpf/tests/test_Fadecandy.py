from unittest.mock import MagicMock
import json

from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSocket


class TestFadecandy(MpfTestCase):
    def getConfigFile(self):
        return 'fadecandy.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/openpixel/'

    def get_platform(self):
        return 'fadecandy'

    def setUp(self):
        self._messages = []
        super().setUp()
        color_correct = self._messages.pop(0)
        color_correct_binary = b'\x00\xff\x00Z\x00\x01\x00\x01'
        self.assertEqual(color_correct[0:len(color_correct_binary)], color_correct_binary)
        correction = {"linearSlope": 1.0, "linearCutoff": 0.0, "gamma": 2.5, "whitepoint": [1.0, 1.0, 1.0]}
        self.assertEqual(json.loads(color_correct[len(color_correct_binary):].decode()), correction)

        firmware = self._messages.pop(0)
        self.assertEqual(firmware, b'\x00\xff\x00\x05\x00\x01\x00\x02\x00')

        self.assertOpenPixelLedsSent({}, {})

    def tearDown(self):
        self._messages = []
        super().tearDown()
        # test that we blanked all LEDs at shutdown
        self.assertOpenPixelLedsSent({}, {})

    def _mock_loop(self):
        self._mock_socket = MockSocket()
        self.clock.mock_socket("localhost", 7890, self._mock_socket)
        # connect socket to test
        self._mock_socket.send = self._send_mock

    def _build_message(self, channel, leds):
        out = bytearray()
        out.extend([channel, 0, 1, 44])
        for i in range(0, 100):
            if i in leds:
                out.extend([leds[i][0], leds[i][1], leds[i][2]])
            else:
                out.extend([0, 0, 0])

        return bytes(out)

    def _send_mock(self, message):
        self._messages.append(message)
        return len(message)

    def assertOpenPixelLedsSent(self, leds1, leds2):
        bank1 = self._build_message(0, leds1)
        bank2 = self._build_message(1, leds2)
        found1 = False
        found2 = False
        for message in self._messages:
            if not (message == bank1 or message == bank2):
                print("Received:", ":".join("{:02x}".format(c) for c in message))
                print("Expected bank1:", ":".join("{:02x}".format(c) for c in bank1))
                print("Expected bank2:",":".join("{:02x}".format(c) for c in bank2))
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
        self.machine.lights.test_led.on()
        self.advance_time_and_run(.02)
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, {})

        # test led 20 ond channel 0
        self.machine.lights.test_led2.color(RGBColor((255, 0, 0)))
        self.advance_time_and_run(.02)
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (255, 255, 255)}, {})

        self.machine.lights.test_led.off()
        self.advance_time_and_run(.02)
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (0, 0, 0)}, {})
        self._messages = []

        # test led color
        self.machine.lights.test_led.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(.02)
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (2, 23, 42)}, {})

        # test led on channel 1
        self.machine.lights.test_led3.on()
        self.advance_time_and_run(.02)
        self._messages = []
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (2, 23, 42)}, {99: (255, 255, 255)})

        self.machine.lights.test_led.off()
        self.machine.lights.test_led2.off()
        self.machine.lights.test_led3.off()
        self.advance_time_and_run(.02)
        self._messages = []
        self.advance_time_and_run(.1)
        self.assertOpenPixelLedsSent({}, {})
        self.machine.lights.test_led.color("blue", priority=5, fade_ms=20, key="test2")
        self.advance_time_and_run()

        self.machine.lights.test_led.on(priority=10, fade_ms=1000, key="test")
        self.advance_time_and_run(2)
        self._messages = []
        self.advance_time_and_run(.1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, {})
        # test crossfade on same key
        self._messages = []
        self.machine.lights.test_led.on(priority=10, fade_ms=1000, key="test")
        self.advance_time_and_run(.1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, {})

        # test remove and readd
        self._messages = []
        self.machine.lights.test_led.remove_from_stack_by_key(fade_ms=1000, key="test")
        self.machine.lights.test_led.on(priority=10, fade_ms=1000, key="test")
        self.advance_time_and_run(.1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, {})

        # test fade out
        self.machine.lights.test_led.remove_from_stack_by_key(fade_ms=1000, key="test")
        self.advance_time_and_run(.5)
        self._messages = []
        self.advance_time_and_run(.1)
        message = self._build_message(0, {99: (113, 113, 255)})
        self.assertIn(message, self._messages)
        self.advance_time_and_run(.5)
        self._messages = []
        self.advance_time_and_run(.1)
        self.assertOpenPixelLedsSent({99: (0, 0, 255)}, {})

        # fade over fade
        self.machine.lights.test_led.on(priority=10, key="test")
        self.machine.lights.test_led.remove_from_stack_by_key(fade_ms=10000, key="test2")
        self.advance_time_and_run(.1)
        self._messages = []
        self.advance_time_and_run(.1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, {})
        self.machine.lights.test_led.remove_from_stack_by_key(fade_ms=1000, key="test")
        self.advance_time_and_run(.5)
        self.advance_time_and_run(20)
        self._messages = []
        self.advance_time_and_run(.1)
        self.assertOpenPixelLedsSent({99: (0, 0, 0)}, {})
