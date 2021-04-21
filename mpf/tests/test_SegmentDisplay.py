from mpf.devices.segment_display.transitions import NoTransition, PushTransition, CoverTransition, UncoverTransition, \
    WipeTransition
from mpf.devices.segment_display.segment_display_text import SegmentDisplayText
from mpf.platforms.interfaces.segment_display_platform_interface import FlashingType
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

    def test_transitions(self):
        # no transition
        transition = NoTransition("12345", "ABCDE", 5, False, False, {'direction': 'right'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(1, len(transition_steps))
        self.assertEqual("ABCDE", transition_steps[0])

        # push right
        transition = PushTransition("12345", "ABCDE", 5, False, False, {'direction': 'right'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("E1234", transition_steps[0])
        self.assertEqual("DE123", transition_steps[1])
        self.assertEqual("CDE12", transition_steps[2])
        self.assertEqual("BCDE1", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # push left
        transition = PushTransition("12345", "ABCDE", 5, False, False, {'direction': 'left'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("2345A", transition_steps[0])
        self.assertEqual("345AB", transition_steps[1])
        self.assertEqual("45ABC", transition_steps[2])
        self.assertEqual("5ABCD", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # push split out (odd display length)
        transition = PushTransition("12345", "ABCDE", 5, False, False, {'direction': 'split_out'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(3, len(transition_steps))
        self.assertEqual("23C45", transition_steps[0])
        self.assertEqual("3BCD4", transition_steps[1])
        self.assertEqual("ABCDE", transition_steps[2])

        # push split out (even display length)
        transition = PushTransition("123456", "ABCDEF", 6, False, False, {'direction': 'split_out'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(3, len(transition_steps))
        self.assertEqual("23CD45", transition_steps[0])
        self.assertEqual("3BCDE4", transition_steps[1])
        self.assertEqual("ABCDEF", transition_steps[2])

        # push split in (odd display length)
        transition = PushTransition("12345", "ABCDE", 5, False, False, {'direction': 'split_in'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(3, len(transition_steps))
        self.assertEqual("C234D", transition_steps[0])
        self.assertEqual("BC3DE", transition_steps[1])
        self.assertEqual("ABCDE", transition_steps[2])

        # push split in (even display length)
        transition = PushTransition("123456", "ABCDEF", 6, False, False, {'direction': 'split_in'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(3, len(transition_steps))
        self.assertEqual("C2345D", transition_steps[0])
        self.assertEqual("BC34DE", transition_steps[1])
        self.assertEqual("ABCDEF", transition_steps[2])

        # push right (display larger than text)
        transition = PushTransition("12345", "ABCDE", 8, False, False, {'direction': 'right'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(8, len(transition_steps))
        self.assertEqual("E   1234", transition_steps[0])
        self.assertEqual("DE   123", transition_steps[1])
        self.assertEqual("CDE   12", transition_steps[2])
        self.assertEqual("BCDE   1", transition_steps[3])
        self.assertEqual("ABCDE   ", transition_steps[4])
        self.assertEqual(" ABCDE  ", transition_steps[5])
        self.assertEqual("  ABCDE ", transition_steps[6])
        self.assertEqual("   ABCDE", transition_steps[7])

        # push left (display larger than text)
        transition = PushTransition("12345", "ABCDE", 8, False, False, {'direction': 'left'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(8, len(transition_steps))
        self.assertEqual("  12345 ", transition_steps[0])
        self.assertEqual(" 12345  ", transition_steps[1])
        self.assertEqual("12345   ", transition_steps[2])
        self.assertEqual("2345   A", transition_steps[3])
        self.assertEqual("345   AB", transition_steps[4])
        self.assertEqual("45   ABC", transition_steps[5])
        self.assertEqual("5   ABCD", transition_steps[6])
        self.assertEqual("   ABCDE", transition_steps[7])

        # push right (collapse commas)
        transition = PushTransition("1,000", "25,000", 5, False, True, {'direction': 'right'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("0 1,00", transition_steps[0])
        self.assertEqual("00 1,0", transition_steps[1])
        self.assertEqual("000 1,", transition_steps[2])
        self.assertEqual("5,000 ", transition_steps[3])
        self.assertEqual("25,000", transition_steps[4])

        # push left (collapse commas)
        transition = PushTransition("1,000", "25,000", 5, False, True, {'direction': 'left'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("1,0002", transition_steps[0])
        self.assertEqual("00025,", transition_steps[1])
        self.assertEqual("0025,0", transition_steps[2])
        self.assertEqual("025,00", transition_steps[3])
        self.assertEqual("25,000", transition_steps[4])

        # cover right
        transition = CoverTransition("12345", "ABCDE", 5, False, False, {'direction': 'right'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("E2345", transition_steps[0])
        self.assertEqual("DE345", transition_steps[1])
        self.assertEqual("CDE45", transition_steps[2])
        self.assertEqual("BCDE5", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # cover left
        transition = CoverTransition("12345", "ABCDE", 5, False, False, {'direction': 'left'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("1234A", transition_steps[0])
        self.assertEqual("123AB", transition_steps[1])
        self.assertEqual("12ABC", transition_steps[2])
        self.assertEqual("1ABCD", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # uncover right
        transition = UncoverTransition("12345", "ABCDE", 5, False, False, {'direction': 'right'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("A1234", transition_steps[0])
        self.assertEqual("AB123", transition_steps[1])
        self.assertEqual("ABC12", transition_steps[2])
        self.assertEqual("ABCD1", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # uncover left
        transition = UncoverTransition("12345", "ABCDE", 5, False, False, {'direction': 'left'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("2345E", transition_steps[0])
        self.assertEqual("345DE", transition_steps[1])
        self.assertEqual("45CDE", transition_steps[2])
        self.assertEqual("5BCDE", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # wipe right
        transition = WipeTransition("12345", "ABCDE", 5, False, False, {'direction': 'right'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("A2345", transition_steps[0])
        self.assertEqual("AB345", transition_steps[1])
        self.assertEqual("ABC45", transition_steps[2])
        self.assertEqual("ABCD5", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # wipe left
        transition = WipeTransition("12345", "ABCDE", 5, False, False, {'direction': 'left'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(5, len(transition_steps))
        self.assertEqual("1234E", transition_steps[0])
        self.assertEqual("123DE", transition_steps[1])
        self.assertEqual("12CDE", transition_steps[2])
        self.assertEqual("1BCDE", transition_steps[3])
        self.assertEqual("ABCDE", transition_steps[4])

        # wipe split (odd output length)
        transition = WipeTransition("12345", "ABCDE", 5, False, False, {'direction': 'split'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(3, len(transition_steps))
        self.assertEqual("12C45", transition_steps[0])
        self.assertEqual("1BCD5", transition_steps[1])
        self.assertEqual("ABCDE", transition_steps[2])

        # wipe split (even output length)
        transition = WipeTransition("123456", "ABCDEF", 6, False, False, {'direction': 'split'})
        transition_steps = list(map(SegmentDisplayText.to_str, transition.transition_steps))

        self.assertEqual(3, len(transition_steps))
        self.assertEqual("12CD56", transition_steps[0])
        self.assertEqual("1BCDE6", transition_steps[1])
        self.assertEqual("ABCDEF", transition_steps[2])
