from mpf.tests.MpfGameTestCase import MpfGameTestCase
from mpf.tests.MpfTestCase import test_config


class TestAttract(MpfGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/game/'

    def get_platform(self):
        return 'smart_virtual'

    def testAttractLoadingAndUnloading(self):
        self.assertNumBallsKnown(0)

        self.assertModeRunning("attract")
        self.assertModeNotRunning("game")

        # ball search is not running because we are missing enough balls
        self.assertFalse(self.machine.playfield.ball_search.enabled)
        self.assertFalse(self.machine.playfield.ball_search.started)

        # cannot start game
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()
        self.assertModeRunning("attract")
        self.assertModeNotRunning("game")
        # this should start ball search
        self.assertTrue(self.machine.playfield.ball_search.enabled)
        self.assertTrue(self.machine.playfield.ball_search.started)

        self.fill_troughs()
        self.advance_time_and_run()

        # start a three ball one player game
        self.start_game()
        for i in range(3):
            self.advance_time_and_run(1)
            self.assertModeNotRunning("attract")
            self.assertModeRunning("game")
            self.advance_time_and_run(9)
            self.drain_all_balls()

        self.advance_time_and_run(1)

        self.assertModeRunning("attract")
        self.assertModeNotRunning("game")

        self.assertFalse(self.machine.playfield.ball_search.enabled)
        self.assertFalse(self.machine.playfield.ball_search.started)

    @test_config("config_with_balls.yaml")
    def testAttractLoadingWithOneBallInTrough(self):
        self.assertNumBallsKnown(1)

        self.assertModeRunning("attract")
        self.assertModeNotRunning("game")

        # ball search is not running because we are missing enough balls
        self.assertTrue(self.machine.playfield.ball_search.enabled)
        self.assertTrue(self.machine.playfield.ball_search.started)

        # cannot start game
        self.assertGameIsNotRunning()
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertGameIsNotRunning()
        self.assertModeRunning("attract")
        self.assertModeNotRunning("game")

        self.fill_troughs()
        self.advance_time_and_run()

        # start a three ball one player game
        self.start_game()
        for i in range(3):
            self.advance_time_and_run(1)
            self.assertModeNotRunning("attract")
            self.assertModeRunning("game")
            self.advance_time_and_run(9)
            self.drain_all_balls()

        self.advance_time_and_run(1)

        self.assertModeRunning("attract")
        self.assertModeNotRunning("game")
