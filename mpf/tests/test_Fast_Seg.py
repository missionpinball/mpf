# mpf.tests.test_Fast_Seg (Segment Displays)

from mpf.tests.test_Fast import TestFastBase
from mpf.tests.MpfTestCase import test_config

class TestFastSeg(TestFastBase):
    """Tests the FAST Audio Interface boards."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['seg']

    def get_config_file(self):
        return 'seg.yaml'

    def create_expected_commands(self):
        # self.serial_connections['seg'].expected_commands = {
        #         'PA:00,       ': '',}
        pass

    def test_seg(self):
        # This was migrated from MPF 0.56 and has not been tested with real hardware.
        # There's a chance it doesn't actually work, but should be simple to fix.

        self.assertEqual(5, len(self.machine.segment_displays))

        seg_addresses = list()

        # Make sure the MPF segment interface is picking up the digits and colors
        for seg in self.machine.segment_displays:
            for digit_color in seg.colors:
                self.assertEqual('ffffff', digit_color.hex)
            for digit_text in seg.text:
                self.assertEqual(' ', digit_text)

            num_digits = seg.size
            fast_address = seg.hw_display.hex_id
            seg_addresses.append(fast_address)

            # make sure the commands sent via FSP match the lengths of digits
            self.assertEqual(len(self.seg_cpu.seg_digits[fast_address]), num_digits)
            self.assertEqual(len(self.seg_cpu.seg_colors[fast_address]), num_digits)

        # Make sure the serial commands went out
        for display, colors in self.seg_cpu.seg_colors.items():
            for digit in colors:
                self.assertEqual('FFFFFF', digit)