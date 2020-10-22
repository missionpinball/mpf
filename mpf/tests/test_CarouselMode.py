from mpf.tests.MpfTestCase import MpfTestCase, MagicMock


class TestCarouselMode(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
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

    def testBlockingCarousel(self):
        self.mock_event("blocking_carousel_item1_highlighted")
        self.mock_event("blocking_carousel_item2_highlighted")
        self.mock_event("blocking_carousel_item3_highlighted")
        self.mock_event("flipper_cancel")
        
        self._start_game()
        self.post_event("start_mode4")

        self.assertIn(self.machine.modes["blocking_carousel"], self.machine.mode_controller.active_modes)
        self.assertEqual(1, self._events["blocking_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["blocking_carousel_item2_highlighted"]) 
        self.post_event("s_flipper_right_active")
        self.post_event("s_flipper_right_inactive")
        self.assertEqual(1, self._events["blocking_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["blocking_carousel_item3_highlighted"]) 
        self.assertEqual(0, self._events["flipper_cancel"]) 
        self.post_event("s_flipper_right_active")
        self.post_event("s_flipper_left_active")
        self.post_event("flipper_cancel")
        self.post_event("s_flipper_right_inactive")
        self.post_event("s_flipper_left_inactive")
        self.assertEqual(1, self._events["flipper_cancel"])
        self.assertEqual(1, self._events["blocking_carousel_item1_highlighted"])
        self.assertEqual(1, self._events["blocking_carousel_item2_highlighted"]) 
        self.assertEqual(0, self._events["blocking_carousel_item3_highlighted"]) 
        self.post_event("both_flippers_inactive")
        self.post_event("s_flipper_right_inactive")
        self.assertEqual(1, self._events["blocking_carousel_item3_highlighted"]) 

        # Restart the mode to ensure that the block is cleared
        self.post_event("flipper_cancel")
        self.post_event("stop_mode4")
        self.advance_time_and_run()
        self.post_event("start_mode4")
        self.post_event("s_flipper_right_inactive")
        self.assertEqual(2, self._events["blocking_carousel_item2_highlighted"], 
            "item2_highlighted should be called when a blocked mode restarts") 

    def testConditionalCarousel(self):
        self.mock_event("conditional_carousel_item1_highlighted")
        self.mock_event("conditional_carousel_item2_highlighted")
        self.mock_event("conditional_carousel_item3_highlighted")
        self.mock_event("conditional_carousel_item4_highlighted")

        self._start_game()

        # Start the mode without any conditions true
        self.post_event("start_mode3")
        self.assertIn(self.machine.modes["conditional_carousel"], self.machine.mode_controller.active_modes)
        self.assertEqual(1, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("next")
        self.assertEqual(2, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("next")
        self.assertEqual(3, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("stop_mode3")

        # Reset the count for item 1
        self.mock_event("conditional_carousel_item1_highlighted")
        # Start the mode with a player variable condition
        self.machine.game.player["show_item4"] = True
        self.post_event("start_mode3")
        self.assertEqual(1, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("next")
        self.assertEqual(1, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(1, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("next")
        self.assertEqual(2, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(1, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("stop_mode3")

        # Reset the count for items 1 and 4
        self.mock_event("conditional_carousel_item1_highlighted")
        self.mock_event("conditional_carousel_item4_highlighted")
        # Start the mode with a machine variable condition
        self.machine.variables.set_machine_var("player2_score", 500000)
        self.machine.game.player["show_item4"] = False
        self.post_event("start_mode3")
        self.assertEqual(1, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("next")
        self.assertEqual(1, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(1, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("next")
        self.assertEqual(2, self._events["conditional_carousel_item1_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item2_highlighted"])
        self.assertEqual(1, self._events["conditional_carousel_item3_highlighted"])
        self.assertEqual(0, self._events["conditional_carousel_item4_highlighted"])
        self.post_event("stop_mode3")

        # The mode shouldn't start if all conditions are false (i.e. no items)
        self.mock_event("conditional_carousel_items_empty")
        self.machine.game.player["hide_item1"] = "truthy"
        self.machine.variables.set_machine_var("player2_score", 0)
        self.post_event("start_mode3")
        self.assertEqual(1, self._events["conditional_carousel_items_empty"])
        self.assertNotIn(self.machine.modes["conditional_carousel"], self.machine.mode_controller.active_modes)

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
        self.assertIn(self.machine.modes["carousel"], self.machine.mode_controller.active_modes)

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

        self.assertNotIn(self.machine.modes["carousel"], self.machine.mode_controller.active_modes)
