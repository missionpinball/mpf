from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestShots(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/segment_display/'

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

        self.post_event("test_event3")
        self.advance_time_and_run()

        self.assertEqual("", display1.hw_display.text)
        self.assertEqual("", display2.hw_display.text)

        self.post_event("test_score")
        self.advance_time_and_run()

        self.assertEqual("1: ", display1.hw_display.text)
        self.assertEqual("2: ", display2.hw_display.text)

        self.machine.set_machine_var("test", 42)
        self.advance_time_and_run()

        self.assertEqual("1: ", display1.hw_display.text)
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
