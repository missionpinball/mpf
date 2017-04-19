from mpf.tests.MpfTestCase import MpfTestCase, MagicMock


class TestCarouselMode(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/carousel/'

    def _start_game(self):
        self.machine.playfield.add_ball = MagicMock()
        self.machine.ball_controller.num_balls_known = 3
        self.hit_and_release_switch("s_start")
        self.advance_time_and_run()
        self.assertIsNotNone(self.machine.game)

    def _stop_game(self):
        # stop game
        self.assertIsNotNone(self.machine.game)
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    def testExtraBall(self):
        self.mock_event("carousel_item1_highlighted")
        self.mock_event("carousel_item1_selected")
        self.mock_event("carousel_item2_highlighted")
        self.mock_event("carousel_item2_selected")
        self.mock_event("carousel_item3_highlighted")
        self.mock_event("carousel_item3_selected")

        # start game
        self._start_game()
        # start mode
        self.post_event("start_mode1")
        self.assertIn(self.machine.modes.carousel, self.machine.mode_controller.active_modes)

        self.assertEqual(1, self._events["carousel_item1_highlighted"])
        self.assertEqual(0, self._events["carousel_item2_highlighted"])
        self.assertEqual(0, self._events["carousel_item3_highlighted"])

        self.post_event("next")
        self.assertEqual(1, self._events["carousel_item1_highlighted"])
        self.assertEqual(1, self._events["carousel_item2_highlighted"])
        self.assertEqual(0, self._events["carousel_item3_highlighted"])

        self.post_event("next")
        self.assertEqual(1, self._events["carousel_item1_highlighted"])
        self.assertEqual(1, self._events["carousel_item2_highlighted"])
        self.assertEqual(1, self._events["carousel_item3_highlighted"])

        self.post_event("next")
        self.assertEqual(2, self._events["carousel_item1_highlighted"])
        self.assertEqual(1, self._events["carousel_item2_highlighted"])
        self.assertEqual(1, self._events["carousel_item3_highlighted"])

        self.post_event("previous2")
        self.assertEqual(2, self._events["carousel_item1_highlighted"])
        self.assertEqual(1, self._events["carousel_item2_highlighted"])
        self.assertEqual(2, self._events["carousel_item3_highlighted"])

        self.post_event("previous")
        self.assertEqual(2, self._events["carousel_item1_highlighted"])
        self.assertEqual(2, self._events["carousel_item2_highlighted"])
        self.assertEqual(2, self._events["carousel_item3_highlighted"])

        self.post_event("select")
        self.assertEqual(0, self._events["carousel_item1_selected"])
        self.assertEqual(1, self._events["carousel_item2_selected"])
        self.assertEqual(0, self._events["carousel_item3_selected"])

        self.assertNotIn(self.machine.modes.carousel, self.machine.mode_controller.active_modes)