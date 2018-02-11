from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestSegmentDisplay(MpfFakeGameTestCase):

    def getConfigFile(self):
        if self._testMethodName == "test_game":
            return 'game.yaml'
        else:
            return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/segment_display/'

    def test_game(self):
        """Test segment displays in a game for the documentation."""
        display1 = self.machine.segment_displays.display1
        display2 = self.machine.segment_displays.display2
        display3 = self.machine.segment_displays.display3
        display4 = self.machine.segment_displays.display4
        display5 = self.machine.segment_displays.display5

        self.assertEqual("", display1.hw_display.text)
        self.assertEqual("", display2.hw_display.text)
        self.assertEqual("", display3.hw_display.text)
        self.assertEqual("", display4.hw_display.text)
        self.assertEqual("", display5.hw_display.text)
        self.start_game()

        self.assertEqual("0", display1.hw_display.text)
        self.assertTrue(display1.hw_display.flashing)
        self.assertEqual("", display2.hw_display.text)
        self.assertFalse(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("1", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

        self.add_player()
        self.assertEqual("0", display1.hw_display.text)
        self.assertTrue(display1.hw_display.flashing)
        self.assertEqual("0", display2.hw_display.text)
        self.assertFalse(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("1", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

        self.machine.game.player.score += 100
        self.advance_time_and_run()
        self.assertEqual("100", display1.hw_display.text)

        self.drain_ball()
        self.assertEqual("100", display1.hw_display.text)
        self.assertFalse(display1.hw_display.flashing)
        self.assertEqual("0", display2.hw_display.text)
        self.assertTrue(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("1", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

        self.machine.game.player.score += 23
        self.advance_time_and_run()
        self.assertEqual("100", display1.hw_display.text)
        self.assertEqual("23", display2.hw_display.text)

        self.drain_ball()
        self.assertEqual("100", display1.hw_display.text)
        self.assertTrue(display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertFalse(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("2", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

        self.drain_ball()
        self.assertEqual("100", display1.hw_display.text)
        self.assertFalse(display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertTrue(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("2", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

        self.drain_ball()
        self.assertEqual("100", display1.hw_display.text)
        self.assertTrue(display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertFalse(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("3", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

        self.drain_ball()
        self.assertEqual("100", display1.hw_display.text)
        self.assertFalse(display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertTrue(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("3", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

        # game ended
        self.drain_ball()
        self.assertGameIsNotRunning()
        self.assertEqual("100", display1.hw_display.text)
        self.assertFalse(display1.hw_display.flashing)
        self.assertEqual("23", display2.hw_display.text)
        self.assertFalse(display2.hw_display.flashing)
        self.assertEqual("", display3.hw_display.text)
        self.assertFalse(display3.hw_display.flashing)
        self.assertEqual("", display4.hw_display.text)
        self.assertFalse(display4.hw_display.flashing)
        self.assertEqual("", display5.hw_display.text)
        self.assertFalse(display5.hw_display.flashing)

    def test_player(self):
        display1 = self.machine.segment_displays.display1
        display2 = self.machine.segment_displays.display2

        self.post_event("test_event1")
        self.advance_time_and_run()

        self.assertEqual("HELLO1", display1.hw_display.text)
        self.assertEqual("HELLO2", display2.hw_display.text)

        self.post_event("test_event2")
        self.advance_time_and_run()

        self.assertEqual("", display1.hw_display.text)
        self.assertEqual("HELLO2", display2.hw_display.text)

        self.post_event("test_flashing")
        self.assertEqual(True, display1.hw_display.flashing)

        self.post_event("test_no_flashing")
        self.assertEqual(False, display1.hw_display.flashing)

        self.post_event("test_event3")
        self.advance_time_and_run()

        self.assertEqual("", display1.hw_display.text)
        self.assertEqual("", display2.hw_display.text)

        self.post_event("test_score")
        self.advance_time_and_run()

        self.assertEqual("1: 0", display1.hw_display.text)
        self.assertEqual("2: 0", display2.hw_display.text)

        self.machine.set_machine_var("test", 42)
        self.advance_time_and_run()

        self.assertEqual("1: 0", display1.hw_display.text)
        self.assertEqual("2: 42", display2.hw_display.text)

        self.start_game()
        self.machine.game.player.score += 100
        self.advance_time_and_run()
        self.assertEqual("1: 100", display1.hw_display.text)
        self.assertEqual("2: 42", display2.hw_display.text)

        self.machine.game.player.score += 23
        self.machine.set_machine_var("test", 1337)
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

        self.machine.modes.mode1.start()
        self.advance_time_and_run(.1)
        self.assertEqual("MODE1", display1.hw_display.text)
        self.assertEqual("MODE1", display2.hw_display.text)

        self.machine.modes.mode1.stop()
        self.advance_time_and_run(7)
        self.assertEqual("1: 123", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

        self.machine.modes.mode1.start()
        self.advance_time_and_run(5)
        self.assertEqual("MODE1", display1.hw_display.text)
        self.assertEqual("MODE1", display2.hw_display.text)

        self.advance_time_and_run(5)
        self.assertEqual("MODE1", display1.hw_display.text)
        self.assertEqual("2: 1337", display2.hw_display.text)

    def test_scoring(self):
        display1 = self.machine.segment_displays.display1
        display2 = self.machine.segment_displays.display2

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
