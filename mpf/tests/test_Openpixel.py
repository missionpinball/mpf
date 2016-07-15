"""Test openpixel hardware interface."""
from mpf.core.rgb_color import RGBColor
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.tests.loop import MockSocket


class TestOpenpixel(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/openpixel/'

    def get_platform(self):
        return 'openpixel'

    def setUp(self):
        self._messages = []
        super().setUp()
        self.assertOpenPixelLedsSent({}, {})
        self.assertTrue(self._mock_socket.is_open)

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
        self.assertEqual([self._build_message(0, leds1),
                          self._build_message(1, leds2)],
                         self._messages)
        self._messages = []

    def test_led_color(self):
        # test led on channel 0. position 99
        self.machine.leds.test_led.on()
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, {})

        # test led 20 ond channel 0
        self.machine.leds.test_led2.color(RGBColor((255, 0, 0)))
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (255, 255, 255)}, {})

        self.machine.leds.test_led.off()
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (0, 0, 0)}, {})
        self._messages = []

        # test led color
        self.machine.leds.test_led.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (2, 23, 42)}, {})

        # test led on channel 1
        self.machine.leds.test_led3.on()
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (2, 23, 42)}, {99: (255, 255, 255)})

    def test_configure_led(self):
        # test configure_led with int format
        led = self.machine.default_platform.configure_led({"number": "10"}, 3)
        self.assertEqual(10, led.led)

        # test configure_led with hex format
        self.machine.config['open_pixel_control']['number_format'] = "hex"
        led = self.machine.default_platform.configure_led({"number": "10"}, 3)
        self.assertEqual(16, led.led)
