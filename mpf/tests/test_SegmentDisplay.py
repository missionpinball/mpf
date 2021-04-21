from unittest.mock import patch, call, ANY, Mock

from mpf.devices.segment_display.transitions import NoTransition, PushTransition, CoverTransition, UncoverTransition, \
    WipeTransition, TransitionRunner
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType, \
    SegmentDisplaySoftwareFlashPlatformInterface
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfTestCase import test_config


class TestSegmentDisplay(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/segment_display/'

    @test_config("game.yaml")
    def test_game(self):
        """Test segment displays in a game for the documentation."""
        display1 = self.machine.segment_displays["display1"]
        display2 = self.machine.segment_displays["display2"]
        display3 = self.machine.segment_displays["display3"]
        display4 = self.machine.segment_displays["display4"]
        display5 = self.machine.segment_displays["display5"]

        self.assertEqual("", display1.hw_display.text)
        self.assertEqual("", display2.hw_display.text)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual("", display5.hw_display.text)
        self.start_game()

        self.assertEqual("0", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("1", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.add_player()
        self.assertEqual("0", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("0", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("1", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.machine.game.player.score += 100
        self.advance_time_and_run()
        self.assertEqual("100", display1.hw_display.text)

        self.drain_all_balls()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("0", display2.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("1", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.machine.game.player.score += 23
        self.advance_time_and_run()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual("23", display2.hw_display.text)

        self.drain_all_balls()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("2", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.drain_all_balls()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("2", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.drain_all_balls()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("3", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        self.drain_all_balls()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertEqual(FlashingType.FLASH_ALL, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("3", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

        # game ended
        self.drain_all_balls()
        self.assertGameIsNotRunning()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display4.hw_display.flashing)
        self.assertEqual("", display5.hw_display.text)
        self.assertEqual(FlashingType.NO_FLASH, display5.hw_display.flashing)

    def test_player(self):
        display1 = self.machine.segment_displays["display1"]
        display2 = self.machine.segment_displays["display2"]

        self.post_event("test_event1")
        self.advance_time_and_run()

        self.assertEqual("HELLO1", display1.hw_display.text)
        self.assertEqual("HELLO2", display2.hw_display.text)

        self.post_event("test_event2")
        self.advance_time_and_run()

        self.assertEqual("", display1.hw_display.text)
        self.assertEqual("HELLO2", display2.hw_display.text)

        self.post_event("test_flashing")
        self.assertEqual(FlashingType.FLASH_ALL, display1.hw_display.flashing)

        self.post_event("test_no_flashing")
        self.assertEqual(FlashingType.NO_FLASH, display1.hw_display.flashing)

        self.post_event("test_event3")
        self.advance_time_and_run()

        self.assertEqual("", display1.hw_display.text)
        self.assertEqual("", display2.hw_display.text)

        self.post_event("test_score")
        self.advance_time_and_run()

        self.assertEqual("1: 0", display1.hw_display.text)
        self.assertEqual("2: 0", display2.hw_display.text)

        self.machine.variables.set_machine_var("test", 42)
        self.advance_time_and_run()

        self.assertEqual("1: 0", display1.hw_display.text)
        self.assertEqual("2: 42", display2.hw_display.text)

        self.start_game()
        self.machine.game.player.score += 100
        self.advance_time_and_run()
        self.assertEqual("1: 100", display1.hw_display.text)
        self.assertEqual("2: 42", display2.hw_display.text)

        self.machine.game.player.score += 23
        self.machine.variables.set_machine_var("test", 1337)
        self.advance_time_and_run()
        self.assertEqual("1: 123", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.post_event("test_flash")
        self.advance_time_and_run(.1)
        self.assertEqual("TEST", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.advance_time_and_run(2)
        self.assertEqual("1: 123", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.machine.modes["mode1"].start()
        self.advance_time_and_run(.1)
        self.assertEqual("MODE1", display1.hw_display.text)
        self.assertEqual("MODE1", display2.hw_display.text)

        self.machine.modes["mode1"].stop()
        self.advance_time_and_run(7)
        self.assertEqual("1: 123", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.machine.modes["mode1"].start()
        self.advance_time_and_run(5)
        self.assertEqual("MODE1", display1.hw_display.text)
        self.assertEqual("MODE1", display2.hw_display.text)

        self.advance_time_and_run(5)
        self.assertEqual("MODE1", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

    def test_scoring(self):
        display1 = self.machine.segment_displays["display1"]
        display2 = self.machine.segment_displays["display2"]

        # default scoring
        self.post_event("test_score_two_player")

        # one player game
        self.start_game()

        # first display shows score. second empty
        self.assertEqual("0", display1.hw_display.text)
        self.assertEqual("0", display2.hw_display.text)

        # player scores
        self.machine.game.player.score += 42
        self.advance_time_and_run(.01)
        self.assertEqual("42", display1.hw_display.text)
        self.assertEqual("0", display2.hw_display.text)

        # add player
        self.add_player()
        self.advance_time_and_run(.01)
        self.assertEqual("42", display1.hw_display.text)
        self.assertEqual("0", display2.hw_display.text)

    @patch("mpf.platforms.interfaces.segment_display_platform_interface.SegmentDisplaySoftwareFlashPlatformInterface.__abstractmethods__", set())
    @patch("mpf.platforms.interfaces.segment_display_platform_interface.SegmentDisplaySoftwareFlashPlatformInterface._set_text")
    def test_software_flash_platform_interface(self, mock_set_text):
        display = SegmentDisplaySoftwareFlashPlatformInterface("1")
        display.set_text("12345 ABCDE", FlashingType.NO_FLASH)
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call("12345 ABCDE")])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

        display.set_text("12345 ABCDE", FlashingType.FLASH_ALL)
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call("12345 ABCDE"), call("")])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

        display.set_text("12345 ABCDE", FlashingType.FLASH_MATCH)
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call("12345 ABCDE"), call("12345 ABC  ")])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

        display.set_text("12345 ABCDE", FlashingType.FLASH_MASK, "FFFFF______")
        display.set_software_flash(False)
        self.assertTrue(mock_set_text.called)
        mock_set_text.assert_has_calls([call("12345 ABCDE"), call("      ABCDE")])
        display.set_software_flash(True)
        mock_set_text.reset_mock()

    def test_segment_display_text(self):
        """Test the SegmentDisplayText class."""

        # text equal to display length
        test_text = SegmentDisplayText("test", 4, False, False)
        self.assertTrue(isinstance(test_text, list))
        self.assertEqual(4, len(test_text))
        self.assertEqual("test", SegmentDisplayText.convert_to_str(test_text))

        # text longer than display
        test_text = SegmentDisplayText("testing", 4, False, False)
        self.assertTrue(isinstance(test_text, list))
        self.assertEqual(4, len(test_text))
        self.assertEqual("ting", SegmentDisplayText.convert_to_str(test_text))

        # text shorter than display
        test_text = SegmentDisplayText("test", 7, False, False)
        self.assertTrue(isinstance(test_text, list))
        self.assertEqual(7, len(test_text))
        self.assertEqual("   test", SegmentDisplayText.convert_to_str(test_text))

        # collapse commas
        test_text = SegmentDisplayText("25,000", 7, False, True)
        self.assertTrue(isinstance(test_text, list))
        self.assertEqual(7, len(test_text))
        self.assertTrue(test_text[3].comma)
        self.assertEqual(ord("5"), test_text[3].char_code)
        self.assertFalse(test_text[4].comma)
        self.assertEqual(ord("0"), test_text[4].char_code)
        self.assertEqual("  25,000", SegmentDisplayText.convert_to_str(test_text))

        # do not collapse commas
        test_text = SegmentDisplayText("25,000", 7, False, False)
        self.assertTrue(isinstance(test_text, list))
        self.assertEqual(7, len(test_text))
        self.assertFalse(test_text[2].comma)
        self.assertEqual(ord("5"), test_text[2].char_code)
        self.assertFalse(test_text[3].comma)
        self.assertEqual(ord(","), test_text[3].char_code)
        self.assertEqual(" 25,000", SegmentDisplayText.convert_to_str(test_text))

        # collapse dots
        test_text = SegmentDisplayText("25.000", 7, True, False)
        self.assertTrue(isinstance(test_text, list))
        self.assertEqual(7, len(test_text))
        self.assertTrue(test_text[3].dot)
        self.assertEqual(ord("5"), test_text[3].char_code)
        self.assertFalse(test_text[4].dot)
        self.assertEqual(ord("0"), test_text[4].char_code)
        self.assertEqual("  25.000", SegmentDisplayText.convert_to_str(test_text))

        # do not collapse dots
        test_text = SegmentDisplayText("25.000", 7, False, False)
        self.assertTrue(isinstance(test_text, list))
        self.assertEqual(7, len(test_text))
        self.assertFalse(test_text[2].dot)
        self.assertEqual(ord("5"), test_text[2].char_code)
        self.assertFalse(test_text[3].dot)
        self.assertEqual(ord("."), test_text[3].char_code)
        self.assertEqual(" 25.000", SegmentDisplayText.convert_to_str(test_text))

    def test_transitions(self):
        """Test segment display text transitions."""
        self._test_no_transition()
        self._test_push_transition()
        self._test_cover_transition()
        self._test_uncover_transition()
        self._test_wipe_transition()

    def _test_no_transition(self):
        """Test no transition."""
        # no transition
        transition = NoTransition(5, False, False, {'direction': 'right'})
        self.assertEqual(1, transition.get_step_count())
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        with self.assertRaises(AssertionError):
            transition.get_transition_step(1, "12345", "ABCDE")

    def _test_push_transition(self):
        """Test push transition."""
        # push right
        transition = PushTransition(5, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("E1234",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("DE123",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("CDE12",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("BCDE1",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

        # push left
        transition = PushTransition(5, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("2345A",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("345AB",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("45ABC",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("5ABCD",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

        # push split out (odd display length)
        transition = PushTransition(5, False, False, {'direction': 'split_out'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("23C45",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("3BCD4",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))

        # push split out (even display length)
        transition = PushTransition(6, False, False, {'direction': 'split_out'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("23CD45",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "123456", "ABCDEF")))
        self.assertEqual("3BCDE4",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "123456", "ABCDEF")))
        self.assertEqual("ABCDEF",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "123456", "ABCDEF")))

        # push split in (odd display length)
        transition = PushTransition(5, False, False, {'direction': 'split_in'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("C234D",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("BC3DE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))

        # push split in (even display length)
        transition = PushTransition(6, False, False, {'direction': 'split_in'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("C2345D",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "123456", "ABCDEF")))
        self.assertEqual("BC34DE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "123456", "ABCDEF")))
        self.assertEqual("ABCDEF",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "123456", "ABCDEF")))

        # push right (display larger than text)
        transition = PushTransition(8, False, False, {'direction': 'right'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("E   1234",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("DE   123",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("CDE   12",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("BCDE   1",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE   ",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))
        self.assertEqual(" ABCDE  ",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(5, "12345", "ABCDE")))
        self.assertEqual("  ABCDE ",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(6, "12345", "ABCDE")))
        self.assertEqual("   ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(7, "12345", "ABCDE")))

        # push left (display larger than text)
        transition = PushTransition(8, False, False, {'direction': 'left'})
        self.assertEqual(8, transition.get_step_count())
        self.assertEqual("  12345 ",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual(" 12345  ",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("12345   ",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("2345   A",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("345   AB",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))
        self.assertEqual("45   ABC",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(5, "12345", "ABCDE")))
        self.assertEqual("5   ABCD",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(6, "12345", "ABCDE")))
        self.assertEqual("   ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(7, "12345", "ABCDE")))

        # push right (collapse commas)
        transition = PushTransition(5, False, True, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("0 1,00",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "1,000", "25,000")))
        self.assertEqual("00 1,0",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "1,000", "25,000")))
        self.assertEqual("000 1,",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "1,000", "25,000")))
        self.assertEqual("5,000 ",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "1,000", "25,000")))
        self.assertEqual("25,000",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "1,000", "25,000")))

        # push left (collapse commas)
        transition = PushTransition(5, False, True, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("1,0002",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "1,000", "25,000")))
        self.assertEqual("00025,",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "1,000", "25,000")))
        self.assertEqual("0025,0",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "1,000", "25,000")))
        self.assertEqual("025,00",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "1,000", "25,000")))
        self.assertEqual("25,000",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "1,000", "25,000")))

    def _test_cover_transition(self):
        """Test cover transition."""
        # cover right
        transition = CoverTransition(5, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("E2345",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("DE345",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("CDE45",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("BCDE5",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

        # cover left
        transition = CoverTransition(5, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("1234A",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("123AB",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("12ABC",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("1ABCD",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

    def _test_uncover_transition(self):
        """Test uncover transition."""
        # uncover right
        transition = UncoverTransition(5, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("A1234",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("AB123",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("ABC12",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("ABCD1",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

        # uncover left
        transition = UncoverTransition(5, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("2345E",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("345DE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("45CDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("5BCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

    def _test_wipe_transition(self):
        """Test wipe transition."""
        # wipe right
        transition = WipeTransition(5, False, False, {'direction': 'right'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("A2345",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("AB345",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("ABC45",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("ABCD5",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

        # wipe left
        transition = WipeTransition(5, False, False, {'direction': 'left'})
        self.assertEqual(5, transition.get_step_count())
        self.assertEqual("1234E",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("123DE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("12CDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))
        self.assertEqual("1BCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(3, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(4, "12345", "ABCDE")))

        # wipe split (odd output length)
        transition = WipeTransition(5, False, False, {'direction': 'split'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("12C45",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "12345", "ABCDE")))
        self.assertEqual("1BCD5",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "12345", "ABCDE")))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "12345", "ABCDE")))

        # wipe split (even output length)
        transition = WipeTransition(6, False, False, {'direction': 'split'})
        self.assertEqual(3, transition.get_step_count())
        self.assertEqual("12CD56",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(0, "123456", "ABCDEF")))
        self.assertEqual("1BCDE6",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(1, "123456", "ABCDEF")))
        self.assertEqual("ABCDEF",
                         SegmentDisplayText.convert_to_str(transition.get_transition_step(2, "123456", "ABCDEF")))

    def test_transition_runner(self):
        """Test the transition runner using an iterator."""
        transition_iterator = iter(TransitionRunner(self.machine,
                                                    PushTransition(5, False, False, {'direction': 'right'}),
                                                    "12345", "ABCDE"))
        self.assertEqual("E1234",
                         SegmentDisplayText.convert_to_str(next(transition_iterator)))
        self.assertEqual("DE123",
                         SegmentDisplayText.convert_to_str(next(transition_iterator)))
        self.assertEqual("CDE12",
                         SegmentDisplayText.convert_to_str(next(transition_iterator)))
        self.assertEqual("BCDE1",
                         SegmentDisplayText.convert_to_str(next(transition_iterator)))
        self.assertEqual("ABCDE",
                         SegmentDisplayText.convert_to_str(next(transition_iterator)))

        with self.assertRaises(StopIteration):
            next(transition_iterator)

    @patch("mpf.devices.segment_display.segment_display.SegmentDisplay._update_display")
    def test_transitions_with_player(self, mock_update_display):
        self.post_event("test_transition")
        self.advance_time_and_run(3)
        self.assertTrue(mock_update_display.called)
        self.assertEqual(21, mock_update_display.call_count)
        mock_update_display.assert_has_calls([call('          '),
                                              call('          '),
                                              call('L         '),
                                              call('LL        '),
                                              call('OLL       '),
                                              call('ROLL      '),
                                              call('CROLL     '),
                                              call('SCROLL    '),
                                              call(' SCROLL   '),
                                              call('  SCROLL  '),
                                              call('  SCROLL  '),
                                              call(' SCROLL   '),
                                              call('SCROLL    '),
                                              call('CROLL     '),
                                              call('ROLL      '),
                                              call('OLL       '),
                                              call('LL        '),
                                              call('L         '),
                                              call('          '),
                                              call('          '),
                                              call('          ')])
        mock_update_display.reset_mock()

        self.post_event("test_transition_2")
        self.advance_time_and_run(1)
        self.assertTrue(mock_update_display.called)
        self.assertEqual(6, mock_update_display.call_count)
        mock_update_display.assert_has_calls([call('    45    '),
                                              call('   3456   '),
                                              call('  234567  '),
                                              call(' 12345678 '),
                                              call('0123456789'),
                                              call('0123456789')])
        mock_update_display.reset_mock()

        self.post_event("test_transition_3")
        self.advance_time_and_run(1)
        self.assertTrue(mock_update_display.called)
        self.assertEqual(11, mock_update_display.call_count)
        mock_update_display.assert_has_calls([call('A012345678'),
                                              call('AB01234567'),
                                              call('ABC0123456'),
                                              call('ABCD012345'),
                                              call('ABCDE01234'),
                                              call('ABCDEF0123'),
                                              call('ABCDEFG012'),
                                              call('ABCDEFGH01'),
                                              call('ABCDEFGHI0'),
                                              call('ABCDEFGHIJ'),
                                              call('ABCDEFGHIJ')])
        mock_update_display.reset_mock()
