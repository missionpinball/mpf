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
        if leds1 is not None and leds2 is not None:
            self.assertEqual([self._build_message(0, leds1),
                              self._build_message(1, leds2)],
                             self._messages)
        elif leds1 is not None:
            self.assertEqual([self._build_message(0, leds1)],
                             self._messages)
        elif leds2 is not None:
            self.assertEqual([self._build_message(1, leds2)],
                             self._messages)
        else:
            raise AssertionError("Invalid assert")
        self._messages = []

    def test_led_color(self):
        # test led on channel 0. position 99
        self.machine.lights.test_led.on()
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({99: (255, 255, 255)}, None)

        # test led 20 ond channel 0
        self.machine.lights.test_led2.color(RGBColor((255, 0, 0)))
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (255, 255, 255)}, None)

        self.machine.lights.test_led.off()
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (0, 0, 0)}, None)
        self._messages = []

        # test led color
        self.machine.lights.test_led.color(RGBColor((2, 23, 42)))
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent({20: (255, 0, 0), 99: (2, 23, 42)}, None)

        # test led on channel 1
        self.machine.lights.test_led3.on()
        self.advance_time_and_run(1)
        self.assertOpenPixelLedsSent(None, {99: (255, 255, 255)})
