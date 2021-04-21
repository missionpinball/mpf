from mpf.tests.MpfTestCase import MpfTestCase


class TestLightSegmentDisplays(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/light_segment_displays/'

    def get_platform(self):
        return None

    def test_scoring(self):
        display1 = self.machine.segment_displays["display1"]

        # this should show the last two characters 37
        self.post_event("show_1337")
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

        self.post_event("display1_color_red_green_blue_yellow")
        self.assertLightColor("segment1_a", "blue")
        self.assertLightColor("segment1_b", "blue")
        self.assertLightColor("segment1_c", "blue")
        self.assertLightColor("segment1_d", "blue")
        self.assertLightColor("segment1_e", "off")
        self.assertLightColor("segment1_f", "off")
        self.assertLightColor("segment1_g", "blue")
        self.assertLightColor("segment2_a", "yellow")
        self.assertLightColor("segment2_b", "yellow")
        self.assertLightColor("segment2_c", "yellow")
        self.assertLightColor("segment2_d", "off")
        self.assertLightColor("segment2_e", "off")
        self.assertLightColor("segment2_f", "off")
        self.assertLightColor("segment2_g", "off")

        self.post_event("display1_color_white")
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
        self.post_event("show_88")
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
        self.post_event("show_11")
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

        self.post_event("remove_text_display1")

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

        display2 = self.machine.segment_displays["display2"]

        self.assertLightColor("segment3_x0", "off")
        self.assertLightColor("segment3_x1", "off")
        self.assertLightColor("segment3_x2", "off")
        self.assertLightColor("segment3_x3", "off")
        self.assertLightColor("segment4_x0", "off")
        self.assertLightColor("segment4_x1", "off")
        self.assertLightColor("segment4_x2", "off")
        self.assertLightColor("segment4_x3", "off")

        # this should translate 87 to bcd 0001 1110
        display2.add_text("87")
        self.advance_time_and_run()

        self.assertLightColor("segment3_x0", "off")
        self.assertLightColor("segment3_x1", "off")
        self.assertLightColor("segment3_x2", "off")
        self.assertLightColor("segment3_x3", "on")
        self.assertLightColor("segment4_x0", "on")
        self.assertLightColor("segment4_x1", "on")
        self.assertLightColor("segment4_x2", "on")
        self.assertLightColor("segment4_x3", "off")

        display2.set_flashing(True)
        self.assertLightFlashing("segment3_x3", "white", secs=2)
