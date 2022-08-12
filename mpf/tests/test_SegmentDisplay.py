"""Test segment displays."""
from unittest.mock import patch, call

from mpf.core.rgb_color import RGBColor
from mpf.devices.segment_display.transitions import NoTransition, PushTransition, CoverTransition, UncoverTransition, \
    WipeTransition, TransitionRunner, SplitTransition
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText, ColoredSegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType, \
    SegmentDisplaySoftwareFlashPlatformInterface
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfTestCase import test_config
from mpf.platforms.virtual import VirtualSegmentDisplay


class TestSegmentDisplay(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/segment_display/'

    def test_integrated_dots_and_commas(self):
        display1 = self.machine.segment_displays["display1"]
        display4 = self.machine.segment_displays["display4"]
        display5 = self.machine.segment_displays["display5"]

        # help the IDE with types and assert that our test works as expected
        assert isinstance(display1.hw_display, VirtualSegmentDisplay)
        self.assertEqual(10, display1.size)
        self.assertFalse(display1.config['integrated_commas'])
        self.assertFalse(display1.config['integrated_dots'])
        self.assertEqual("          ", display1.hw_display.text)

        assert isinstance(display4.hw_display, VirtualSegmentDisplay)
        self.assertEqual(10, display4.size)
        self.assertTrue(display4.config['integrated_commas'])
        self.assertFalse(display4.config['integrated_dots'])
        self.assertEqual("          ", display4.hw_display.text)

        assert isinstance(display5.hw_display, VirtualSegmentDisplay)
        self.assertEqual(10, display5.size)
        self.assertFalse(display5.config['integrated_commas'])
        self.assertTrue(display5.config['integrated_dots'])
        self.assertEqual("          ", display5.hw_display.text)

        # add a 10-digit number (no dots or commas)
        display1.add_text("1234567890")
        self.assertEqual("1234567890", display1.hw_display.text)
        display4.add_text("1234567890")
        self.assertEqual("1234567890", display4.hw_display.text)
        display5.add_text("1234567890")
        self.assertEqual("1234567890", display5.hw_display.text)

        # add a 10-digit number with integrated commas (displays without integrated commas will be truncated)
        display1.add_text("1,234,567,890")
        self.assertEqual("34,567,890", display1.hw_display.text)
        display4.add_text("1,234,567,890")
        self.assertEqual("1,234,567,890", display4.hw_display.text)
        display5.add_text("1,234,567,890")
        self.assertEqual("34,567,890", display5.hw_display.text)

        # add a 10-digit number with integrated dots (displays without integrated dots will be truncated)
        display1.add_text("1.234.567.890")
        self.assertEqual("34.567.890", display1.hw_display.text)
        display4.add_text("1.234.567.890")
        self.assertEqual("34.567.890", display4.hw_display.text)
        display5.add_text("1.234.567.890")
        self.assertEqual("1.234.567.890", display5.hw_display.text)

    @test_config("game.yaml")
    def test_game(self):
        """Test segment displays in a game for the documentation."""
        display1 = self.machine.segment_displays["display1"]
        display2 = self.machine.segment_displays["display2"]
        display3 = self.machine.segment_displays["display3"]
        display4 = self.machine.segment_displays["display4"]
        display5 = self.machine.segment_displays["display5"]

        # help the IDE with types and assert that our test works as expected
        assert isinstance(display1.hw_display, VirtualSegmentDisplay)
        assert isinstance(display2.hw_display, VirtualSegmentDisplay)
        assert isinstance(display3.hw_display, VirtualSegmentDisplay)
        assert isinstance(display4.hw_display, VirtualSegmentDisplay)
        assert isinstance(display5.hw_display, VirtualSegmentDisplay)

        self.assertEqual("       ", display1.hw_display.text)
        self.assertEqual("       ", display2.hw_display.text)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual("       ", display5.hw_display.text)
        self.start_game()

        self.assertEqual("      0", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("       ", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("      1", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.add_player()
        self.assertEqual("      0", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("      0", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("      1", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.machine.game.player.score += 100
        self.advance_time_and_run()
        self.assertEqual("    100", display1.hw_display.text)

        self.drain_all_balls()
        self.assertEqual("    100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("      0", display2.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("      1", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.machine.game.player.score += 23
        self.advance_time_and_run()
        self.assertEqual("    100", display1.hw_display.text)
        self.assertEqual("     23", display2.hw_display.text)

        self.drain_all_balls()
        self.assertEqual("    100", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("     23", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("      2", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.drain_all_balls()
        self.assertEqual("    100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("     23", display2.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("      2", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.drain_all_balls()
        self.assertEqual("    100", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("     23", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("      3", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.drain_all_balls()
        self.assertEqual("    100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("     23", display2.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("      3", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        # game ended
        self.drain_all_balls()
        self.assertGameIsNotRunning()
        self.assertEqual("    100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("     23", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("       ", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("       ", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("       ", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

    def test_player(self):
        display1 = self.machine.segment_displays["display1"]
        display2 = self.machine.segment_displays["display2"]

        # help the IDE with types and assert that our test works as expected
        assert isinstance(display1.hw_display, VirtualSegmentDisplay)
        assert isinstance(display2.hw_display, VirtualSegmentDisplay)

        self.post_event("test_event1")
        self.advance_time_and_run()

        self.assertEqual("    HELLO1", display1.hw_display.text)
        self.assertEqual(" HELLO2", display2.hw_display.text)

        self.post_event("test_event2")
        self.advance_time_and_run()

        self.assertEqual("          ", display1.hw_display.text)
        self.assertEqual(" HELLO2", display2.hw_display.text)

        self.post_event("test_flashing")
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)

        self.post_event("test_no_flashing")
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)

        self.post_event("test_event3")
        self.advance_time_and_run()

        self.assertEqual("          ", display1.hw_display.text)
        self.assertEqual("       ", display2.hw_display.text)

        self.post_event("test_score")
        self.advance_time_and_run()

        self.assertEqual("      1: 0", display1.hw_display.text)
        self.assertEqual("   2: 0", display2.hw_display.text)

        self.machine.variables.set_machine_var("test", 42)
        self.advance_time_and_run()

        self.assertEqual("      1: 0", display1.hw_display.text)
        self.assertEqual("  2: 42", display2.hw_display.text)

        self.start_game()
        self.machine.game.player.score += 100
        self.advance_time_and_run()
        self.assertEqual("    1: 100", display1.hw_display.text)
        self.assertEqual("  2: 42", display2.hw_display.text)

        self.machine.game.player.score += 23
        self.machine.variables.set_machine_var("test", 1337)
        self.advance_time_and_run()
        self.assertEqual("    1: 123", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.post_event("test_flash")
        self.advance_time_and_run(.1)
        self.assertEqual("      TEST", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.advance_time_and_run(2)
        self.assertEqual("    1: 123", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.machine.modes["mode1"].start()
        self.advance_time_and_run(.1)
        self.assertEqual("     MODE1", display1.hw_display.text)
        self.assertEqual("  MODE1", display2.hw_display.text)

        self.machine.modes["mode1"].stop()
        self.advance_time_and_run(7)
        self.assertEqual("    1: 123", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.machine.modes["mode1"].start()
        self.advance_time_and_run(5)
        self.assertEqual("     MODE1", display1.hw_display.text)
        self.assertEqual("  MODE1", display2.hw_display.text)

        self.advance_time_and_run(5)
        self.assertEqual("     MODE1", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

    def test_scoring(self):
        display1 = self.machine.segment_displays["display1"]
        display2 = self.machine.segment_displays["display2"]

        # help the IDE with types and assert that our test works as expected
        assert isinstance(display1.hw_display, VirtualSegmentDisplay)
        assert isinstance(display2.hw_display, VirtualSegmentDisplay)

        # default scoring
        self.post_event("test_score_two_player")

        # one player game
        self.start_game()

        # first display shows score. second empty
        self.assertEqual("         0", display1.hw_display.text)
        self.assertEqual("      0", display2.hw_display.text)

        # player scores
        self.machine.game.player.score += 42
        self.advance_time_and_run(.01)
        self.assertEqual("        42", display1.hw_display.text)
        self.assertEqual("      0", display2.hw_display.text)

        # add player
        self.add_player()
        self.advance_time_and_run(.01)
        self.assertEqual("        42", display1.hw_display.text)
        self.assertEqual("      0", display2.hw_display.text)

    @patch("mpf.platforms.interfaces.segment_display_platform_interface.SegmentDisplaySoftwareFlashPlatformInterface"
           ".__abstractmethods__", set())
    @patch("mpf.platforms.interfaces.segment_display_platform_interface.SegmentDisplaySoftwareFlashPlatformInterface"
           "._set_text")
    def test_software_flash_platform_interface(self, mock_set_text):
        display = SegmentDisplaySoftwareFlashPlatformInterface("1")
        text = SegmentDisplayText.from_str("12345 ABCDE", 10, True, True, False)
        display.set_text(text, FlashingType.NO_FLASH, '')
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call(text)])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

        display.set_text(text, FlashingType.FLASH_ALL, '')
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call(SegmentDisplayText.from_str("", 10, True, True, False))])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

        display.set_text(text, FlashingType.FLASH_MATCH, '')
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call(SegmentDisplayText.from_str("12345 ABC  ", 10, True, True, False))])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

        display.set_text(text, FlashingType.FLASH_MASK, "FFFFF______")
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call(SegmentDisplayText.from_str("      ABCDE", 10, True, True, False))])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

    def test_segment_display_text(self):
        """Test the SegmentDisplayText class."""

        # text equal to display length
        test_text = SegmentDisplayText.from_str("test", 4, False, False, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(4, len(test_text))
        self.assertEqual("test", test_text.convert_to_str())

        # text longer than display
        test_text = SegmentDisplayText.from_str("testing", 4, False, False, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(4, len(test_text))
        self.assertEqual("ting", test_text.convert_to_str())

        # text shorter than display
        test_text = SegmentDisplayText.from_str("test", 7, False, False, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(7, len(test_text))
        self.assertEqual("   test", test_text.convert_to_str())

        # collapse commas
        test_text = SegmentDisplayText.from_str("25,000", 7, False, True, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(7, len(test_text))
        self.assertTrue(test_text[3].comma)
        self.assertEqual(ord("5"), test_text[3].char_code)
        self.assertFalse(test_text[4].comma)
        self.assertEqual(ord("0"), test_text[4].char_code)
        self.assertEqual("  25,000", test_text.convert_to_str())

        # collapse commas and use dots for commas
        test_text = SegmentDisplayText.from_str("25,000", 7, False, True, True)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(7, len(test_text))
        self.assertTrue(test_text[3].dot)
        self.assertEqual(ord("5"), test_text[3].char_code)
        self.assertFalse(test_text[4].dot)
        self.assertEqual(ord("0"), test_text[4].char_code)
        self.assertEqual("  25.000", test_text.convert_to_str())

        # use dots for commas
        test_text = SegmentDisplayText.from_str("25,000", 7, False, False, True)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(7, len(test_text))
        self.assertTrue(test_text[3].dot)
        self.assertEqual(ord("5"), test_text[3].char_code)
        self.assertFalse(test_text[4].dot)
        self.assertEqual(ord("0"), test_text[4].char_code)
        self.assertEqual("  25.000", test_text.convert_to_str())

        # do not collapse commas
        test_text = SegmentDisplayText.from_str("25,000", 7, False, False, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(7, len(test_text))
        self.assertFalse(test_text[2].comma)
        self.assertEqual(ord("5"), test_text[2].char_code)
        self.assertFalse(test_text[3].comma)
        self.assertEqual(ord(","), test_text[3].char_code)
        self.assertEqual(" 25,000", test_text.convert_to_str())

        # collapse dots
        test_text = SegmentDisplayText.from_str("25.000", 7, True, False, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(7, len(test_text))
        self.assertTrue(test_text[3].dot)
        self.assertEqual(ord("5"), test_text[3].char_code)
        self.assertFalse(test_text[4].dot)
        self.assertEqual(ord("0"), test_text[4].char_code)
        self.assertEqual("  25.000", test_text.convert_to_str())

        # do not collapse dots
        test_text = SegmentDisplayText.from_str("25.000", 7, False, False, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(7, len(test_text))
        self.assertFalse(test_text[2].dot)
        self.assertEqual(ord("5"), test_text[2].char_code)
        self.assertFalse(test_text[3].dot)
        self.assertEqual(ord("."), test_text[3].char_code)
        self.assertEqual(" 25.000", test_text.convert_to_str())

        # no colors
        test_text = SegmentDisplayText.from_str("COLOR", 5, False, False, False)
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(5, len(test_text))
        colors = test_text.get_colors()
        self.assertIsNone(colors)

        # single color
        test_text = SegmentDisplayText.from_str("COLOR", 5, False, False, False, [RGBColor("ffffff")])
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(5, len(test_text))
        colors = test_text.get_colors()
        self.assertEqual(5, len(colors))
        self.assertEqual(5, colors.count(RGBColor("ffffff")))

        # multiple colors
        test_text = SegmentDisplayText.from_str("COLOR", 5, False, False, False,
                                                [RGBColor("white"), RGBColor("red"), RGBColor("green"),
                                                 RGBColor("blue"),
                                                 RGBColor("cyan")])
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(5, len(test_text))
        colors = test_text.get_colors()
        self.assertEqual(5, len(colors))
        self.assertEqual([RGBColor("white"), RGBColor("red"), RGBColor("green"),
                          RGBColor("blue"), RGBColor("cyan")], colors)

        # multiple colors (fewer colors than letters)
        test_text = SegmentDisplayText.from_str("COLOR", 5, False, False, False,
                                                [RGBColor("white"), RGBColor("red")])
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(5, len(test_text))
        colors = test_text.get_colors()
        self.assertEqual(5, len(colors))
        self.assertEqual([RGBColor("white"), RGBColor("red"), RGBColor("red"),
                          RGBColor("red"), RGBColor("red")], colors)

        # multiple colors (fewer colors than letters and fewer letters than characters)
        test_text = SegmentDisplayText.from_str("COLOR", 8, False, False, False,
                                                [RGBColor("white"), RGBColor("red")])
        self.assertTrue(isinstance(test_text, SegmentDisplayText))
        self.assertEqual(8, len(test_text))
        colors = test_text.get_colors()
        self.assertEqual(8, len(colors))
        self.assertEqual([RGBColor("white"), RGBColor("white"), RGBColor("white"), RGBColor("white"),
                          RGBColor("red"), RGBColor("red"), RGBColor("red"), RGBColor("red")], colors)

    def test_transitions(self):
        """Test segment display text transitions."""
        self._test_no_transition()
        self._test_push_transition()
        self._test_cover_transition()
        self._test_uncover_transition()
        self._test_wipe_transition()
        self._test_split_transition()

    def _test_no_transition(self):
        """Test no transition."""
        # no transition (with colors)
        transition = NoTransition(5, False, False, False, {'direction': 'right'})
        self.assertEqual(1, transition.get_step_count())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("green")],
                         transition.get_transition_step(0, "12345", "ABCDE",
                                                        [RGBColor("red")], [RGBColor("green")]).get_colors())
        with self.assertRaises(AssertionError):
            transition.get_transition_step(1, "12345", "ABCDE")

    def _test_push_transition(self):
        """Test push transition."""
        # push right (with colors)
        transition = PushTransition(5, False, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("E1234",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("red"), RGBColor("red"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(0, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("DE123",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("red"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(1, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("CDE12",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(2, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("BCDE1",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("red")],
                         transition.get_transition_step(3, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("green")],
                         transition.get_transition_step(4, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())

        # push left
        transition = PushTransition(5, False, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("2345A",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("345AB",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("45ABC",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("5ABCD",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())

        # push right (display larger than text)
        transition = PushTransition(8, False, False, False, {'direction': 'right'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("E   1234",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("DE   123",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("CDE   12",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("BCDE   1",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE   ",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual(" ABCDE  ",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("  ABCDE ",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("   ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

        # push left (display larger than text)
        transition = PushTransition(8, False, False, False, {'direction': 'left'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("  12345 ",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual(" 12345  ",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("12345   ",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("2345   A",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("345   AB",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("45   ABC",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("5   ABCD",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("   ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

        # push right (collapse commas)
        transition = PushTransition(5, False, True, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("0 1,00",
                         transition.get_transition_step(0, "1,000", "25,000").convert_to_str())
        self.assertEqual("00 1,0",
                         transition.get_transition_step(1, "1,000", "25,000").convert_to_str())
        self.assertEqual("000 1,",
                         transition.get_transition_step(2, "1,000", "25,000").convert_to_str())
        self.assertEqual("5,000 ",
                         transition.get_transition_step(3, "1,000", "25,000").convert_to_str())
        self.assertEqual("25,000",
                         transition.get_transition_step(4, "1,000", "25,000").convert_to_str())

        # push left (collapse commas)
        transition = PushTransition(5, False, True, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("1,0002",
                         transition.get_transition_step(0, "1,000", "25,000").convert_to_str())
        self.assertEqual("00025,",
                         transition.get_transition_step(1, "1,000", "25,000").convert_to_str())
        self.assertEqual("0025,0",
                         transition.get_transition_step(2, "1,000", "25,000").convert_to_str())
        self.assertEqual("025,00",
                         transition.get_transition_step(3, "1,000", "25,000").convert_to_str())
        self.assertEqual("25,000",
                         transition.get_transition_step(4, "1,000", "25,000").convert_to_str())

        # push right (with text and colors)
        transition = PushTransition(5, False, False, False,
                                    {'direction': 'right', 'text': '-->', 'text_color': [RGBColor("yellow")]})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual(">1234",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("yellow"), RGBColor("red"), RGBColor("red"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(0, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("->123",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("yellow"), RGBColor("yellow"), RGBColor("red"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(1, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("-->12",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("yellow"), RGBColor("yellow"), RGBColor("yellow"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(2, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("E-->1",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("yellow"), RGBColor("yellow"),
                          RGBColor("yellow"), RGBColor("red")],
                         transition.get_transition_step(3, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("DE-->",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("yellow"),
                          RGBColor("yellow"), RGBColor("yellow")],
                         transition.get_transition_step(4, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("CDE--",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("yellow"), RGBColor("yellow")],
                         transition.get_transition_step(5, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("BCDE-",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("yellow")],
                         transition.get_transition_step(6, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("green")],
                         transition.get_transition_step(7, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())

        # push right (with text that has color = None and colors)
        transition = PushTransition(5, False, False, False,
                                    {'direction': 'right', 'text': '-->', 'text_color': None})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual(">1234",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("red"), RGBColor("red"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(0, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("->123",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("red"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(1, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("-->12",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("red"), RGBColor("red")],
                         transition.get_transition_step(2, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("E-->1",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("red")],
                         transition.get_transition_step(3, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("DE-->",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("green")],
                         transition.get_transition_step(4, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("CDE--",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("green")],
                         transition.get_transition_step(5, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("BCDE-",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("green")],
                         transition.get_transition_step(6, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())
        self.assertEqual([RGBColor("green"), RGBColor("green"), RGBColor("green"),
                          RGBColor("green"), RGBColor("green")],
                         transition.get_transition_step(7, "12345", "ABCDE", [RGBColor("red")],
                                                        [RGBColor("green")]).get_colors())

        # push left (with text)
        transition = PushTransition(5, False, False, False, {'direction': 'left', 'text': "<--"})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("2345<",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("345<-",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("45<--",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("5<--A",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("<--AB",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("--ABC",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("-ABCD",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

    def _test_cover_transition(self):
        """Test cover transition."""
        # cover right
        transition = CoverTransition(5, False, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("E2345",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("DE345",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("CDE45",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("BCDE5",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())

        # cover right (with text)
        transition = CoverTransition(5, False, False, False, {'direction': 'right', 'text': '-->'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual(">2345",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("->345",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("-->45",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("E-->5",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("DE-->",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("CDE--",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("BCDE-",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

        # cover left
        transition = CoverTransition(5, False, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("1234A",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("123AB",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("12ABC",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("1ABCD",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())

        # cover left (with text)
        transition = CoverTransition(5, False, False, False, {'direction': 'left', 'text': '<--'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("1234<",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("123<-",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("12<--",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("1<--A",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("<--AB",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("--ABC",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("-ABCD",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

    def _test_uncover_transition(self):
        """Test uncover transition."""
        # uncover right
        transition = UncoverTransition(5, False, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("A1234",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("AB123",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABC12",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCD1",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())

        # uncover right (with text)
        transition = UncoverTransition(5, False, False, False, {'direction': 'right', 'text': '-->'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual(">1234",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("->123",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("-->12",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("A-->1",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("AB-->",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABC--",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCD-",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

        # uncover left
        transition = UncoverTransition(5, False, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("2345E",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("345DE",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("45CDE",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("5BCDE",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())

        # uncover left (with text)
        transition = UncoverTransition(5, False, False, False, {'direction': 'left', 'text': '<--'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("2345<",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("345<-",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("45<--",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("5<--E",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("<--DE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("--CDE",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("-BCDE",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

    def _test_wipe_transition(self):
        """Test wipe transition."""
        # wipe right
        transition = WipeTransition(5, False, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("A2345",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("AB345",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABC45",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCD5",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())

        # wipe right (with text)
        transition = WipeTransition(5, False, False, False, {'direction': 'right', 'text': '-->'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual(">2345",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("->345",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("-->45",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("A-->5",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("AB-->",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABC--",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCD-",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

        # wipe left
        transition = WipeTransition(5, False, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("1234E",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("123DE",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("12CDE",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("1BCDE",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())

        # wipe left (with text)
        transition = WipeTransition(5, False, False, False, {'direction': 'left', 'text': '<--'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("1234<",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("123<-",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("12<--",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())
        self.assertEqual("1<--E",
                         transition.get_transition_step(3, "12345", "ABCDE").convert_to_str())
        self.assertEqual("<--DE",
                         transition.get_transition_step(4, "12345", "ABCDE").convert_to_str())
        self.assertEqual("--CDE",
                         transition.get_transition_step(5, "12345", "ABCDE").convert_to_str())
        self.assertEqual("-BCDE",
                         transition.get_transition_step(6, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(7, "12345", "ABCDE").convert_to_str())

    def _test_split_transition(self):
        # split push out (odd display length)
        transition = SplitTransition(5, False, False, False, {'direction': 'out', 'mode': 'push'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("23C45",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("3BCD4",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())

        # split push out (even display length)
        transition = SplitTransition(6, False, False, False, {'direction': 'out', 'mode': 'push'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("23CD45",
                         transition.get_transition_step(0, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("3BCDE4",
                         transition.get_transition_step(1, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("ABCDEF",
                         transition.get_transition_step(2, "123456", "ABCDEF").convert_to_str())

        # split push in (odd display length)
        transition = SplitTransition(5, False, False, False, {'direction': 'in', 'mode': 'push'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("C234D",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("BC3DE",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())

        # split push in (even display length)
        transition = SplitTransition(6, False, False, False, {'direction': 'in', 'mode': 'push'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("C2345D",
                         transition.get_transition_step(0, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("BC34DE",
                         transition.get_transition_step(1, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("ABCDEF",
                         transition.get_transition_step(2, "123456", "ABCDEF").convert_to_str())

        # split wipe out (odd output length)
        transition = SplitTransition(5, False, False, False, {'direction': 'out', 'mode': 'wipe'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("12C45",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("1BCD5",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())

        # split wipe out (even output length)
        transition = SplitTransition(6, False, False, False, {'direction': 'out', 'mode': 'wipe'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("12CD56",
                         transition.get_transition_step(0, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("1BCDE6",
                         transition.get_transition_step(1, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("ABCDEF",
                         transition.get_transition_step(2, "123456", "ABCDEF").convert_to_str())

        # split wipe in (odd output length)
        transition = SplitTransition(5, False, False, False, {'direction': 'in', 'mode': 'wipe'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("A234E",
                         transition.get_transition_step(0, "12345", "ABCDE").convert_to_str())
        self.assertEqual("AB3DE",
                         transition.get_transition_step(1, "12345", "ABCDE").convert_to_str())
        self.assertEqual("ABCDE",
                         transition.get_transition_step(2, "12345", "ABCDE").convert_to_str())

        # split wipe in (even output length)
        transition = SplitTransition(6, False, False, False, {'direction': 'in', 'mode': 'wipe'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("A2345F",
                         transition.get_transition_step(0, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("AB34EF",
                         transition.get_transition_step(1, "123456", "ABCDEF").convert_to_str())
        self.assertEqual("ABCDEF",
                         transition.get_transition_step(2, "123456", "ABCDEF").convert_to_str())

    def test_transition_runner(self):
        """Test the transition runner using an iterator."""
        transition_iterator = iter(TransitionRunner(self.machine,
                                                    PushTransition(5, False, False, False, {'direction': 'right'}),
                                                    "12345", "ABCDE"))
        self.assertEqual("E1234",
                         next(transition_iterator).convert_to_str())
        self.assertEqual("DE123",
                         next(transition_iterator).convert_to_str())
        self.assertEqual("CDE12",
                         next(transition_iterator).convert_to_str())
        self.assertEqual("BCDE1",
                         next(transition_iterator).convert_to_str())
        self.assertEqual("ABCDE",
                         next(transition_iterator).convert_to_str())

        with self.assertRaises(StopIteration):
            next(transition_iterator)

        # test placeholder evaluation during transitions (includes integrated commas)
        self.machine.variables.set_machine_var("segment_display_test_value", 0)

        transition_iterator = iter(TransitionRunner(self.machine,
                                                    PushTransition(5, False, True, False, {'direction': 'right'}),
                                                    "ABCDE", "{machine.segment_display_test_value:,d}"))

        self.assertEqual("0ABCD",
                         next(transition_iterator).convert_to_str())

        self.machine.variables.set_machine_var("segment_display_test_value", 5)
        self.assertEqual(" 5ABC",
                         next(transition_iterator).convert_to_str())

        self.machine.variables.set_machine_var("segment_display_test_value", 74)
        self.assertEqual(" 74AB",
                         next(transition_iterator).convert_to_str())

        self.machine.variables.set_machine_var("segment_display_test_value", 1234)
        self.assertEqual("1,234A",
                         next(transition_iterator).convert_to_str())

        self.machine.variables.set_machine_var("segment_display_test_value", 54321)
        self.assertEqual("54,321",
                         next(transition_iterator).convert_to_str())

        with self.assertRaises(StopIteration):
            next(transition_iterator)

    @patch("mpf.platforms.virtual.VirtualSegmentDisplay.set_text")
    def test_transitions_with_player(self, mock_set_text):
        red = RGBColor("red")
        wht = RGBColor("white")
        self.post_event("test_set_color_to_red")
        self.advance_time_and_run(1)

        mock_set_text.assert_has_calls(
            [call(
                SegmentDisplayText.from_str_with_color('       ', 7, True, True, False, [red] * 7),
                flash_mask='', flashing=FlashingType.NO_FLASH)])
        mock_set_text.reset_mock()

        self.post_event("test_set_color_to_white")
        self.advance_time_and_run(1)

        mock_set_text.assert_has_calls(
            [call(
                SegmentDisplayText.from_str_with_color('       ', 7, True, True, False, [wht] * 7),
                flash_mask='', flashing=FlashingType.NO_FLASH)])
        mock_set_text.reset_mock()

        self.post_event("test_transition")
        self.advance_time_and_run(3)
        self.assertTrue(mock_set_text.called)
        self.assertEqual(20, mock_set_text.call_count)

        # incoming text is centered so has spaces before and after the new text)
        mock_set_text.assert_has_calls([
            call(
                SegmentDisplayText.from_str_with_color('          ', 10, True, True, False, [red] * 1 + [wht] * 9),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('          ', 10, True, True, False, [red] * 2 + [wht] * 8),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('L         ', 10, True, True, False, [red] * 3 + [wht] * 7),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('LL        ', 10, True, True, False, [red] * 4 + [wht] * 6),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('OLL       ', 10, True, True, False, [red] * 5 + [wht] * 5),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('ROLL      ', 10, True, True, False, [red] * 6 + [wht] * 4),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('CROLL     ', 10, True, True, False, [red] * 7 + [wht] * 3),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('SCROLL    ', 10, True, True, False, [red] * 8 + [wht] * 2),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color(' SCROLL   ', 10, True, True, False, [red] * 9 + [wht] * 1),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('  SCROLL  ', 10, True, True, False, [red] * 10 + [wht] * 0),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color(' SCROLL   ', 10, True, True, False, [red] * 9 + [wht] * 1),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('SCROLL    ', 10, True, True, False, [red] * 8 + [wht] * 2),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('CROLL     ', 10, True, True, False, [red] * 7 + [wht] * 3),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('ROLL      ', 10, True, True, False, [red] * 6 + [wht] * 4),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('OLL       ', 10, True, True, False, [red] * 5 + [wht] * 5),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('LL        ', 10, True, True, False, [red] * 4 + [wht] * 6),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('L         ', 10, True, True, False, [red] * 3 + [wht] * 7),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('          ', 10, True, True, False, [red] * 2 + [wht] * 8),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('          ', 10, True, True, False, [red] * 1 + [wht] * 9),
                flash_mask='', flashing=FlashingType.NO_FLASH),
            call(
                SegmentDisplayText.from_str_with_color('          ', 10, True, True, False, [red] * 0 + [wht] * 10),
                flash_mask='', flashing=FlashingType.NO_FLASH),
        ])
        mock_set_text.reset_mock()

        self.post_event("test_transition_2")
        self.advance_time_and_run(1)
        self.assertTrue(mock_set_text.called)
        self.assertEqual(5, mock_set_text.call_count)
        mock_set_text.assert_has_calls([
            call(SegmentDisplayText.from_str_with_color('    45    ', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('   3456   ', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('  234567  ', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color(' 12345678 ', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('0123456789', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
        ])
        mock_set_text.reset_mock()

        self.post_event("test_transition_3")
        self.advance_time_and_run(1)
        self.assertTrue(mock_set_text.called)
        self.assertEqual(10, mock_set_text.call_count)
        mock_set_text.assert_has_calls([
            call(SegmentDisplayText.from_str_with_color('A012345678', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('AB01234567', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABC0123456', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABCD012345', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABCDE01234', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABCDEF0123', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABCDEFG012', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABCDEFGH01', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABCDEFGHI0', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
            call(SegmentDisplayText.from_str_with_color('ABCDEFGHIJ', 10, True, True, False, [wht] * 10),
                 flash_mask='', flashing=FlashingType.NO_FLASH),
        ])
        mock_set_text.reset_mock()

    @test_config("config_colors.yaml")
    def test_colors_and_transitions(self):
        """Test colors and transitions."""
        self.post_event("test_event1")
        self.advance_time_and_run(.5)
        self.assertEqual("    EVENT1", self.machine.segment_displays["display1"].text)
        self.assertEqual(
            [RGBColor("red"), RGBColor("red"), RGBColor("red"), RGBColor("red"), RGBColor("red"), RGBColor("blue"),
             RGBColor("yellow"), RGBColor("green"), RGBColor("white"), RGBColor("purple")],
            self.machine.segment_displays["display1"].colors)

        self.post_event("test_event2")
        self.advance_time_and_run(2)
        self.assertEqual("    EVENT2", self.machine.segment_displays["display1"].text)
        self.assertEqual(
            [RGBColor("red"), RGBColor("red"), RGBColor("red"), RGBColor("red"), RGBColor("red"), RGBColor("blue"),
             RGBColor("yellow"), RGBColor("green"), RGBColor("white"), RGBColor("purple")],
            self.machine.segment_displays["display1"].colors)

    @test_config("config_flashing.yaml")
    def test_flashing_and_transition(self):
        """Test that flashing workings with transitions."""
        self.post_event("test_event1")
        self.advance_time_and_run(.5)
        self.assertEqual("    EVENT1", self.machine.segment_displays["display1"].text)
        self.assertEqual(FlashingType.FLASH_ALL, self.machine.segment_displays["display1"].flashing)

    @test_config("config_transition.yaml")
    def test_transition_stack(self):
        """Test that lower priority entries do not run transitions on higher priority entries."""
        self.post_event("test_event2")
        self.advance_time_and_run(.5)
        self.assertEqual("    EVENT2", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(4)
        self.assertEqual("    EVENT2", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(1)
        self.assertEqual("          ", self.machine.segment_displays["display1"].text)

        self.post_event("test_event1")
        self.post_event("test_event2")
        self.advance_time_and_run(.5)
        self.assertEqual("    EVENT2", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(4)
        self.assertEqual("    EVENT2", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(1)
        self.assertEqual("          ", self.machine.segment_displays["display1"].text)

        self.post_event("test_event2")
        self.post_event("test_event1")
        self.advance_time_and_run(.5)
        self.assertEqual("    EVENT1", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(1)
        self.assertEqual("    EVENT1", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(1)
        self.assertEqual("          ", self.machine.segment_displays["display1"].text)

        self.post_event("test_event3")
        self.post_event("test_event4")
        self.advance_time_and_run(.5)
        self.assertEqual("    EVENT4", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(4)
        self.assertEqual("    EVENT4", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(1)
        self.assertEqual("          ", self.machine.segment_displays["display1"].text)

        self.post_event("test_event3")
        self.post_event("test_event4")
        self.advance_time_and_run(.5)
        self.assertEqual("    EVENT4", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(4)
        self.assertEqual("    EVENT4", self.machine.segment_displays["display1"].text)
        self.advance_time_and_run(1)
        self.assertEqual("          ", self.machine.segment_displays["display1"].text)

    def test_text_stack(self):
        """Test the segment display text stack functionality."""
        display1 = self.machine.segment_displays["display1"]
        assert isinstance(display1.hw_display, VirtualSegmentDisplay)

        display1.add_text("FIRST")
        self.assertEqual("     FIRST", display1.text)
        self.assertEqual([RGBColor("white")] * 10, display1.colors)
        self.assertEqual([RGBColor("white")] * 10, display1.hw_display.colors)
        self.assertEqual(FlashingType.NO_FLASH, display1.flashing)

        # higher priority and with colors, flashing
        display1.add_text_entry(
            "SECOND", [RGBColor("red")], FlashingType.FLASH_ALL, "", None, None, 10, "2nd")
        self.assertEqual("    SECOND", display1.text)
        self.assertEqual([RGBColor("red")] * 10, display1.colors)
        self.assertEqual(FlashingType.FLASH_ALL, display1.flashing)

        # lower priority
        display1.add_text_entry(
            "THIRD", [RGBColor("yellow")], FlashingType.FLASH_MASK, "F F F ", None, None, 5, "3rd")
        self.assertEqual("    SECOND", display1.text)
        self.assertEqual([RGBColor("red")] * 10, display1.colors)
        self.assertEqual(FlashingType.FLASH_ALL, display1.flashing)

        # remove highest priority item from stack
        display1.remove_text_by_key("2nd")
        self.assertEqual("     THIRD", display1.text)
        self.assertEqual([RGBColor("yellow")] * 10, display1.colors)
        self.assertEqual(FlashingType.FLASH_MASK, display1.flashing)
        self.assertEqual("F F F ", display1.flash_mask)

        # replace current top text
        display1.add_text("3rd", 5, "3rd")
        self.assertEqual("       3rd", display1.text)
        self.assertEqual([RGBColor("yellow")] * 10, display1.colors)
        self.assertEqual(FlashingType.FLASH_MASK, display1.flashing)
        self.assertEqual("F F F ", display1.flash_mask)

        # change text of lowest item
        display1.add_text("1st")
        self.assertEqual("       3rd", display1.text)
        self.assertEqual([RGBColor("yellow")] * 10, display1.colors)
        self.assertEqual(FlashingType.FLASH_MASK, display1.flashing)
        self.assertEqual("F F F ", display1.flash_mask)

        # change text, color, and flashing of lowest item and raise its priority
        display1.add_text_entry(
            "FIRST", [RGBColor("blue")], FlashingType.NO_FLASH, "", None, None, 20, None)
        self.assertEqual("     FIRST", display1.text)
        self.assertEqual([RGBColor("blue")] * 10, display1.colors)

        # remove "FIRST" entry
        display1.remove_text_by_key(None)
        self.assertEqual("       3rd", display1.text)
        self.assertEqual([RGBColor("blue")] * 10, display1.colors)
        self.assertEqual(FlashingType.NO_FLASH, display1.flashing)

        # set flashing
        display1.set_flashing(FlashingType.FLASH_MASK, "FFF   ")
        self.assertEqual([RGBColor("blue")] * 10, display1.colors)
        self.assertEqual(FlashingType.FLASH_MASK, display1.flashing)
        self.assertEqual("FFF   ", display1.flash_mask)

        # set color
        display1.set_color([RGBColor("cyan")])
        self.assertEqual([RGBColor("cyan")] * 10, display1.colors)
        self.assertEqual(FlashingType.FLASH_MASK, display1.flashing)
        self.assertEqual("FFF   ", display1.flash_mask)

        # remove last remaining entry
        display1.remove_text_by_key("3rd")
        self.assertEqual("          ", display1.text)
        self.assertEqual([RGBColor("cyan")] * 10, display1.colors)
        self.assertEqual(FlashingType.NO_FLASH, display1.flashing)
        self.assertEqual("", display1.flash_mask)
