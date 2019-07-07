from mpf.tests.MpfTestCase import MpfTestCase


class TestLightSegmentDisplays(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/light_segment_displays/'

    def get_platform(self):
        return None

    def test_scoring(self):
        display1 = self.machine.segment_displays["display1"]

        # this should show the last two characters 37
        display1.add_text("1337")
        self.advance_time_and_run()

        self.assertLightColor("segment1_a", "on")
        self.assertLightColor("segment1_b", "on")
        self.assertLightColor("segment1_c", "on")
        self.assertLightColor("segment1_d", "on")
        self.assertLightColor("segment1_e", "off")
        self.assertLightColor("segment1_f", "off")
        self.assertLightColor("segment1_g", "on")
        self.assertLightColor("segment2_a", "on")
        self.assertLightColor("segment2_b", "on")
        self.assertLightColor("segment2_c", "on")
        self.assertLightColor("segment2_d", "off")
        self.assertLightColor("segment2_e", "off")
        self.assertLightColor("segment2_f", "off")
        self.assertLightColor("segment2_g", "off")

        # turn on all lights
        display1.add_text("88")
        self.advance_time_and_run()

        self.assertLightColor("segment1_a", "on")
        self.assertLightColor("segment1_b", "on")
        self.assertLightColor("segment1_c", "on")
        self.assertLightColor("segment1_d", "on")
        self.assertLightColor("segment1_e", "on")
        self.assertLightColor("segment1_f", "on")
        self.assertLightColor("segment1_g", "on")
        self.assertLightColor("segment2_a", "on")
        self.assertLightColor("segment2_b", "on")
        self.assertLightColor("segment2_c", "on")
        self.assertLightColor("segment2_d", "on")
        self.assertLightColor("segment2_e", "on")
        self.assertLightColor("segment2_f", "on")
        self.assertLightColor("segment2_g", "on")

        # back to four lights only
        display1.add_text("11")
        self.advance_time_and_run()

        self.assertLightColor("segment1_a", "off")
        self.assertLightColor("segment1_b", "on")
        self.assertLightColor("segment1_c", "on")
        self.assertLightColor("segment1_d", "off")
        self.assertLightColor("segment1_e", "off")
        self.assertLightColor("segment1_f", "off")
        self.assertLightColor("segment1_g", "off")
        self.assertLightColor("segment2_a", "off")
        self.assertLightColor("segment2_b", "on")
        self.assertLightColor("segment2_c", "on")
        self.assertLightColor("segment2_d", "off")
        self.assertLightColor("segment2_e", "off")
        self.assertLightColor("segment2_f", "off")
        self.assertLightColor("segment2_g", "off")

        # set invalid chars (for 7segment). should be "1 "
        display1.add_text("1{}".format(chr(244)))
        self.advance_time_and_run()

        self.assertLightColor("segment1_a", "off")
        self.assertLightColor("segment1_b", "on")
        self.assertLightColor("segment1_c", "on")
        self.assertLightColor("segment1_d", "off")
        self.assertLightColor("segment1_e", "off")
        self.assertLightColor("segment1_f", "off")
        self.assertLightColor("segment1_g", "off")
        self.assertLightColor("segment2_a", "off")
        self.assertLightColor("segment2_b", "off")
        self.assertLightColor("segment2_c", "off")
        self.assertLightColor("segment2_d", "off")
        self.assertLightColor("segment2_e", "off")
        self.assertLightColor("segment2_f", "off")
        self.assertLightColor("segment2_g", "off")
