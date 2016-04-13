from mock import MagicMock

from mpf.core.rgb_color import RGBColor
from mpf.platforms import openpixel
from mpf.tests.MpfTestCase import MpfTestCase


class TestOpenpixel(MpfTestCase):
    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/openpixel/'

    def get_platform(self):
        return 'openpixel'

    def setUp(self):
        self._messages = []
        openpixel.OPCThread = MagicMock()
        openpixel.OpenPixelClient.send = self._send_mock
        super().setUp()
        self.assertOpenPixelLedsSent({}, {})

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