from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestShots(MpfTestCase):

    def get_config_file(self):
        return 'test_shots.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/shots/'

    def setUp(self):
        super(TestShots, self).setUp()
        self.min_frame_time = 0.5

    def start_game(self):
        # shots only work in games so we have to do this a lot
        self.machine.playfield.add_ball = MagicMock()
        self.machine.events.post('game_start')
        self.advance_time_and_run(1.02)
        self.machine.game.balls_in_play = 1
        self.assertIsNotNone(self.machine.game)

    def stop_game(self):
        # stop game
        self.machine.game.end_game()
        self.advance_time_and_run()
        self.assertIsNone(self.machine.game)

    def test_block(self):
        self.mock_event("playfield_active")
        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(.1)
        self.assertEventCalled("playfield_active")

        self.start_game()
        self.assertEqual("unlit", self.machine.shots["shot_3"].state_name)

        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(.1)
        self.assertTrue(self.machine.shots["shot_3"].enabled)
        self.assertEqual("lit", self.machine.shots["shot_3"].state_name)

        self.machine.shots["shot_3"].reset()
        self.assertEqual("unlit", self.machine.shots["shot_3"].state_name)

        # Start the mode and make sure those shots load
        self.start_mode("mode1")

        self.assertTrue(self.machine.shots["shot_3"].enabled)
        self.assertTrue(self.machine.shots["mode1_shot_3"].enabled)
        self.assertEqual("unlit", self.machine.shots["shot_3"].state_name)
        self.assertEqual("mode1_one", self.machine.shots["mode1_shot_3"].state_name)

        self.hit_and_release_switch("switch_3")
        self.advance_time_and_run(.1)

        self.assertEqual("unlit", self.machine.shots["shot_3"].state_name)
        self.assertEqual("mode1_two", self.machine.shots["mode1_shot_3"].state_name)

    def test_loading_shots(self):
        # Make sure machine-wide shots load & mode-specific shots do not
        self.assertIn('shot_1', self.machine.shots)
        self.assertIn('shot_2', self.machine.shots)
        self.assertIn('shot_3', self.machine.shots)
        self.assertIn('shot_4', self.machine.shots)
        self.assertIn('led_1', self.machine.shots)

        self.assertFalse(self.machine.shots["mode1_shot_1"].enabled)

        self.start_game()

        # Start the mode and make sure those shots load
        self.start_mode("mode1")
        self.assertTrue(self.machine.shots["mode1_shot_1"].enabled)

        self.assertIn('shot_1', self.machine.shots)
        self.assertIn('shot_2', self.machine.shots)
        self.assertIn('shot_3', self.machine.shots)
        self.assertIn('shot_4', self.machine.shots)
        self.assertIn('led_1', self.machine.shots)

        # Stop the mode and make sure those shots go away
        self.stop_mode("mode1")
        self.assertFalse(self.machine.shots["mode1_shot_1"].enabled)

        self.assertIn('shot_1', self.machine.shots)
        self.assertIn('shot_2', self.machine.shots)
        self.assertIn('shot_3', self.machine.shots)
        self.assertIn('shot_4', self.machine.shots)
        self.assertIn('led_1', self.machine.shots)

    def test_mode_priorities(self):
        self.start_game()

        # Start the mode
        self.start_mode("mode1")
        # check shot states
        self.assertTrue(self.machine.shots["mode1_shot_2"].enabled)
        self.assertFalse(self.machine.shots["mode2_shot_2"].enabled)
        self.assertLightColor("light_2", "aliceblue")
        self.hit_and_release_switch('switch_2')
        self.assertLightColor("light_2", "antiquewhite")

        self.start_mode("mode2")
        self.assertTrue(self.machine.shots["mode1_shot_2"].enabled)
        self.assertTrue(self.machine.shots["mode2_shot_2"].enabled)

        # mode2 takes priority
        self.assertLightColor("light_2", "red")

        # Stop the mode
        self.stop_mode("mode2")
        self.assertTrue(self.machine.shots["mode1_shot_2"].enabled)
        self.assertFalse(self.machine.shots["mode2_shot_2"].enabled)

        # check if color returns to mode1_shot_2 color
        self.assertLightColor("light_2", "antiquewhite")

    def test_hits(self):
        self.assertFalse(self.machine.shots["mode1_shot_1"].enabled)

        self.shot_1_hit = MagicMock()
        self.shot_1_default_hit = MagicMock()
        self.shot_1_default_unlit_hit = MagicMock()
        self.mode1_shot_1_hit = MagicMock()
        self.machine.events.add_handler('shot_1_hit', self.shot_1_hit)
        self.machine.events.add_handler('shot_1_default_hit',
                                        self.shot_1_default_hit)
        self.machine.events.add_handler('shot_1_default_unlit_hit',
                                        self.shot_1_default_unlit_hit)
        self.machine.events.add_handler('mode1_shot_1_hit',
                                        self.mode1_shot_1_hit)

        # make sure shot does not work with no game in progress
        self.hit_and_release_switch('switch_1')
        self.advance_time_and_run()
        self.shot_1_hit.assert_not_called()

        self.start_game()
        self.start_mode("mode1")
        self.assertTrue(self.machine.shots["mode1_shot_1"].enabled)

        # hit shot_1, test all three event variations
        self.hit_and_release_switch('switch_1')
        self.advance_time_and_run()

        self.shot_1_hit.assert_called_once_with(profile='default',
                                                state='unlit', advancing=True)
        self.shot_1_default_hit.assert_called_once_with(profile='default',
                                                        state='unlit', advancing=True)
        self.shot_1_default_unlit_hit.assert_called_once_with(
            profile='default', state='unlit', advancing=True)

        # hit the mode shot and make sure it was called
        self.hit_and_release_switch('switch_3')
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_called_once_with(profile='default',
                                                      state='unlit', advancing=True)

        # stop the mode
        self.machine.modes["mode1"].stop()
        self.advance_time_and_run()

        # hit the mode shot and make sure it was not called
        self.mode1_shot_1_hit = MagicMock()
        self.hit_and_release_switch('switch_3')
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_not_called()

        # stop the game (should not crash)
        self.stop_game()

        # hit the shot and make sure it was not called again
        self.hit_and_release_switch('switch_1')
        self.advance_time_and_run()
        self.mode1_shot_1_hit.assert_not_called()

    def test_shot_with_multiple_switches(self):
        self.shot_15_hit = MagicMock()
        self.machine.events.add_handler('shot_15_hit', self.shot_15_hit)
        self.start_game()

        # hit shot_15 via switch_13
        self.hit_and_release_switch('switch_13')
        self.shot_15_hit.assert_called_once_with(profile='default',
                                                 state='unlit', advancing=True)

        # hit shot_15 via switch_14
        self.shot_15_hit.reset_mock()
        self.hit_and_release_switch('switch_14')
        self.shot_15_hit.assert_called_once_with(profile='default',
                                                 state='lit', advancing=False)

    def test_shot_with_delay(self):
        self.mock_event("shot_delay_hit")
        self.mock_event("shot_delay_same_switch_hit")
        self.start_game()

        # test delay at the beginning. should not count
        self.hit_and_release_switch("s_delay")
        self.advance_time_and_run(.5)
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(1)
        self.assertEventNotCalled("shot_delay_hit")
        self.advance_time_and_run(3)

        # test shot with same switch for delay and hit
        self.hit_and_release_switch("switch_15")
        self.advance_time_and_run(.5)
        self.assertEventCalled("shot_delay_same_switch_hit")
        self.mock_event("shot_delay_same_switch_hit")
        self.hit_and_release_switch("switch_15")
        self.advance_time_and_run(.5)
        self.assertEventNotCalled("shot_delay_same_switch_hit")

        self.advance_time_and_run(3)
        self.hit_and_release_switch("switch_15")
        self.advance_time_and_run(.5)
        self.assertEventCalled("shot_delay_same_switch_hit")
        self.mock_event("shot_delay_same_switch_hit")

        # test that shot works without delay
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(.5)
        self.assertEventCalled("shot_delay_hit")
        self.mock_event("shot_delay_hit")

        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(.5)
        self.assertEventCalled("shot_delay_hit")
        self.mock_event("shot_delay_hit")
        self.hit_and_release_switch("s_delay")

        self.machine.modes["base2"].stop()
        self.advance_time_and_run()
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(.5)
        self.assertEventNotCalled("shot_delay_hit")

        self.machine.modes["base2"].start()
        self.advance_time_and_run()
        self.hit_and_release_switch("switch_1")
        self.advance_time_and_run(.5)
        self.assertEventCalled("shot_delay_hit")

        self.advance_time_and_run(3)
        self.hit_and_release_switch("switch_15")
        self.advance_time_and_run(.5)
        self.assertEventCalled("shot_delay_same_switch_hit")
        self.mock_event("shot_delay_same_switch_hit")

    def test_profile_advancing_no_loop(self):
        self.start_game()
        self.mock_event("shot_27_hit")
        # unlit and two states in the beginning
        self.assertEqual(2, len(self.machine.shots["shot_1"].config['profile'].config['states']))
        self.assertEqual("unlit", self.machine.shots["shot_1"].state_name)
        self.assertPlaceholderEvaluates("unlit", "device.shots.shot_1.state_name")
        self.assertPlaceholderEvaluates(0, "device.shots.shot_1.state")

        # one hit and it lits
        self.hit_and_release_switch("switch_1")
        self.assertEqual("lit", self.machine.shots["shot_1"].state_name)
        self.assertEqual(1, self.machine.game.player["shot_shot_1"])
        self.assertPlaceholderEvaluates("lit", "device.shots.shot_1.state_name")
        self.assertPlaceholderEvaluates(1, "device.shots.shot_1.state")

        # it stays lit
        self.hit_and_release_switch("switch_1")
        self.assertEqual("lit", self.machine.shots["shot_1"].state_name)
        self.assertEqual(1, self.machine.game.player["shot_shot_1"])
        self.assertEventCalled("shot_27_hit")

    def test_shots_with_events(self):
        self.start_game()
        self.assertModeRunning("base2")
        self.mock_event("shot_28_hit")
        self.post_event("event1")
        self.assertEventCalled("shot_28_hit")

    def test_profile_advancing_with_loop(self):
        self.start_game()

        self.assertEqual(3, len(self.machine.shots["shot_2"].config['profile'].config['states']))

        self.assertEqual("one", self.machine.shots["shot_2"].state_name)

        self.hit_and_release_switch("switch_2")
        self.assertEqual("two", self.machine.shots["shot_2"].state_name)
        self.assertEqual(1, self.machine.game.player["shot_shot_2"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("three", self.machine.shots["shot_2"].state_name)
        self.assertEqual(2, self.machine.game.player["shot_shot_2"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("one", self.machine.shots["shot_2"].state_name)
        self.assertEqual(0, self.machine.game.player["shot_shot_2"])

        self.hit_and_release_switch("switch_2")
        self.assertEqual("two", self.machine.shots["shot_2"].state_name)
        self.assertEqual(1, self.machine.game.player["shot_shot_2"])

    def test_default_show_light(self):
        self.start_game()
        self.assertLightChannel("light_4", 0)

        self.hit_and_release_switch("switch_5")
        self.advance_time_and_run()
        self.assertLightChannel("light_4", 255)

    def test_default_show_lights(self):
        self.start_game()
        self.assertLightChannel("light_5", 0)
        self.assertLightChannel("light_6", 0)

        self.hit_and_release_switch("switch_6")
        self.advance_time_and_run()
        self.assertLightChannel("light_5", 255)
        self.assertLightChannel("light_6", 255)

    def test_default_show_led(self):
        self.start_game()
        self.assertLightColor("led_4", "off")

        self.hit_and_release_switch("switch_7")
        self.advance_time_and_run()

        self.assertLightColor("led_4", "white")

    def test_default_show_leds(self):
        self.start_game()
        self.assertLightColor("led_5", "off")
        self.assertLightColor("led_6", "off")

        self.hit_and_release_switch("switch_8")
        self.advance_time_and_run()

        self.assertLightColor("led_5", "white")
        self.assertLightColor("led_6", "white")

    def test_show_in_shot_profile_root(self):
        self.start_game()
        self.assertLightColor("led_3", "red")

        # make sure the show is not auto advancing
        self.advance_time_and_run(5)
        self.assertLightColor("led_3", "red")

        self.advance_time_and_run(5)
        self.assertLightColor("led_3", "red")

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertLightColor("led_3", "orange")

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertLightColor("led_3", "yellow")

        self.hit_and_release_switch("switch_9")
        self.advance_time_and_run()
        self.assertLightColor("led_3", "green")

        # make sure it stays on green
        self.advance_time_and_run(5)
        self.assertLightColor("led_3", "green")

    def test_show_in_step(self):
        self.start_game()
        # start_game() advances the time 1 sec, so by now we're already on
        # step 2 of the rainbow show
        self.assertLightColor("led_11", "orange")

        # make sure show is advancing on its own
        self.advance_time_and_run(1)
        self.assertLightColor("led_11", "yellow")

        # hit the shot, changes to show1
        self.hit_and_release_switch("switch_11")
        self.advance_time_and_run(0.1)
        self.assertLightColor("led_11", "aliceblue")

        # make sure show is advancing on its own
        self.advance_time_and_run(1)
        self.assertLightColor("led_11", "antiquewhite")

    def test_combined_show_in_profile_root_and_step(self):
        # tests a show defined in a profile root which is used for most steps,
        # but a separate show in certain steps that is used just for that step

        self.start_game()
        self.advance_time_and_run()

        # we're on step 1
        self.assertLightColor("led_12", "red")

        # step 2
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run()
        self.assertLightColor("led_12", "orange")

        # since this is a root show, it should not be advancing on its own, so
        # advance the time a few times and make sure the led doesn't change
        self.advance_time_and_run()
        self.assertLightColor("led_12", "orange")

        self.advance_time_and_run()
        self.assertLightColor("led_12", "orange")

        self.advance_time_and_run()
        self.assertLightColor("led_12", "orange")

        # step 3 is rainbow 2 show, so make sure it switches
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run(0.02)
        self.assertLightColor("led_12", "aliceblue")

        # since this is a show in a step, it should be auto advancing, so keep
        # checking every sec to make sure the colors are changing
        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "antiquewhite")

        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "aquamarine")

        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "azure")

        # it should loop
        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "aliceblue")

        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "antiquewhite")

        # hit the switch, should advance to step 4, which is back to the
        # rainbow show
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "green")

        # show should not be advancing without a hit
        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "green")

        # hit to verify advance
        self.hit_and_release_switch("switch_12")
        self.advance_time_and_run(1)
        self.assertLightColor("led_12", "blue")

    def test_show_ending_no_loop(self):
        # tests that if a show is set to loops: 0, that it truly stops on the
        # last step. Note that loops here is really a setting of the show
        # player, so if this works, that means that all of the show player
        # settings will work in a show tied to a shot.

        self.start_game()
        self.assertLightColor("led_14", "orange")

        self.advance_time_and_run(1)
        self.assertLightColor("led_14", "yellow")

        self.advance_time_and_run(1)
        self.assertLightColor("led_14", "green")

        self.advance_time_and_run(1)
        self.assertLightColor("led_14", "blue")

        self.advance_time_and_run(1)
        self.assertLightColor("led_14", "purple")

        # show is done, but hold is true by default in shows started from shots
        # so make sure the led stays in its final state
        self.advance_time_and_run(1)
        self.assertLightColor("led_14", "purple")

    def test_enable_persist(self):
        self.start_game()

        self.start_mode("mode1")
        self.assertFalse(self.machine.shots["mode1_shot_17"].enabled)
        self.assertTrue(self.machine.shots["mode1_shot_1"].enabled)
        self.assertPlaceholderEvaluates(True, "device.shots.mode1_shot_1.enabled")

        self.stop_mode("mode1")
        self.start_mode("mode1")
        self.assertFalse(self.machine.shots["mode1_shot_17"].enabled)
        self.assertTrue(self.machine.shots["mode1_shot_1"].enabled)

        self.post_event("custom_enable_17")
        self.assertTrue(self.machine.shots["mode1_shot_17"].enabled)
        self.post_event("custom_disable_1")
        self.assertFalse(self.machine.shots["mode1_shot_1"].enabled)
        self.assertPlaceholderEvaluates(False, "device.shots.mode1_shot_1.enabled")

        self.stop_mode("mode1")
        self.assertFalse(self.machine.shots["mode1_shot_17"].enabled)
        self.assertFalse(self.machine.shots["mode1_shot_1"].enabled)

        self.start_mode("mode1")
        self.assertTrue(self.machine.shots["mode1_shot_17"].enabled)
        self.assertFalse(self.machine.shots["mode1_shot_1"].enabled)

    def test_control_events(self):
        # test control events from machine-wide shot
        shot16 = self.machine.shots["shot_16"]
        self.mock_event("shot_16_hit")
        self.start_game()

        # Since this shot has custom enable events, it should not be enabled on
        # game start
        self.assertFalse(shot16.enabled)

        # Also verify hit event does not register a hit
        self.machine.events.post('custom_hit_16')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["shot_16_hit"])

        # test enabling via event
        self.machine.events.post('custom_enable_16')
        self.advance_time_and_run()
        self.assertTrue(shot16.enabled)

        # test hit event
        self.machine.events.post('custom_hit_16')
        self.advance_time_and_run()
        self.assertEqual(1, self._events["shot_16_hit"])
        self.assertEqual('lit', shot16.state_name)

        # test reset event
        self.machine.events.post('custom_reset_16')
        self.advance_time_and_run()
        self.assertEqual(shot16.state_name, 'unlit')

        # test advance event
        self.machine.events.post('custom_advance_16')
        self.advance_time_and_run()
        # hit should not be posted again (still 1 from before)
        self.assertEqual(1, self._events["shot_16_hit"])
        # profile should have advanced though
        self.assertEqual(shot16.state_name, 'lit')

        # test disable event
        self.machine.events.post('custom_disable_16')
        self.advance_time_and_run()
        self.assertFalse(shot16.enabled)

        # hit the shot to make sure it's really disabled
        self.machine.events.post('custom_hit_16')
        self.advance_time_and_run()
        self.assertEqual(1, self._events["shot_16_hit"])  # still 1 from before
        self.assertEqual(shot16.state_name, 'lit')

        self.post_event("custom_enable_16")
        self.assertTrue(self.machine.shots["shot_16"].enabled)

        self.post_event('custom_hit_16')
        self.assertEqual(2, self._events["shot_16_hit"])
        self.assertEqual(shot16.state_name, 'lit')

        # test restart event
        self.machine.events.post('custom_disable_16')
        self.advance_time_and_run()
        # make sure we are disabled and advanced in the profile
        self.assertEqual(shot16.state_name, 'lit')
        self.assertFalse(self.machine.shots["shot_16"].enabled)
        self.machine.events.post('custom_restart_16')
        self.advance_time_and_run()
        self.assertEqual(shot16.state_name, 'unlit')
        self.assertTrue(self.machine.shots["shot_16"].enabled)

        # mode1 is not active, so make sure none of the events from
        # mode1_shot_17

        self.assertFalse(self.machine.shots["mode1_shot_17"].enabled)
        self.mock_event("mode1_shot_17_hit")

        # Also verify hit event does not register a hit
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["mode1_shot_17_hit"])

        # test enabling via event, shot should not work
        self.machine.events.post('custom_enable_17')
        self.advance_time_and_run()

        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["mode1_shot_17_hit"])

        # test reset event, nothing should happen
        self.machine.events.post('custom_reset_17')
        self.advance_time_and_run()

        # test disable event, nothing should happen
        self.machine.events.post('custom_disable_17')
        self.advance_time_and_run()

        # start the mode
        self.machine.modes["mode1"].start()
        self.advance_time_and_run()

        shot17 = self.machine.shots["mode1_shot_17"]

        # Since this shot has custom enable events, it should not be enabled on
        # game start
        self.assertFalse(shot17.enabled)

        # Also verify hit event does not register a hit
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(0, self._events["mode1_shot_17_hit"])

        # test enabling via event
        self.machine.events.post('custom_enable_17')
        self.advance_time_and_run()
        self.assertTrue(shot17.enabled)

        # test hit event
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        self.assertEqual(1, self._events["mode1_shot_17_hit"])
        self.assertEqual(shot17.state_name, 'lit')

        # test reset event
        self.machine.events.post('custom_reset_17')
        self.advance_time_and_run()
        self.assertEqual(shot17.state_name, 'unlit')

        # test disable event
        self.machine.events.post('custom_disable_17')
        self.advance_time_and_run()
        self.assertFalse(shot17.enabled)

        # hit the shot to make sure it's really disabled
        self.machine.events.post('custom_hit_17')
        self.advance_time_and_run()
        # since it's disabled, there should still only be 1 from before
        self.assertEqual(1, self._events["mode1_shot_17_hit"])
        self.assertEqual(shot17.state_name, 'unlit')

    def test_advance(self):
        self.mock_event("shot_17_hit")
        shot17 = self.machine.shots["shot_17"]

        self.start_game()

        # shot profile config has advance_on_hit: false
        self.hit_and_release_switch("switch_17")
        # verify it was hit, but it didn't advance
        self.assertEqual(1, self._events["shot_17_hit"])
        self.assertEqual("one", shot17.state_name)

        # again
        self.hit_and_release_switch("switch_17")
        self.assertEqual(2, self._events["shot_17_hit"])
        self.assertEqual("one", shot17.state_name)

        # manual advance
        shot17.advance()
        shot17.advance()
        self.assertEqual("three", shot17.state_name)

        # hit still doesn't advance
        self.hit_and_release_switch("switch_17")
        self.assertEqual(3, self._events["shot_17_hit"])
        self.assertEqual("three", shot17.state_name)

        # disable the shot, advance should be disabled too
        shot17.disable()
        shot17.advance()
        self.assertEqual(2, self.machine.game.player.shot_shot_17)

        # though we can force it to advance
        shot17.advance(force=True)
        self.assertEqual(3, self.machine.game.player.shot_shot_17)

    def test_show_when_disabled(self):
        # first test show_when_disabled == true

        shot19 = self.machine.shots["shot_19"]

        self.start_game()
        # shot19 config has enable_events: none, so it should be disabled
        self.assertFalse(shot19.enabled)

        # start_game() includes a 1 sec advance time, so by now this show is
        # already on step 2
        self.assertLightColor("led_19", 'orange')

        # make sure the show keeps running
        self.advance_time_and_run()
        self.assertLightColor("led_19", 'yellow')

        # enable the shot
        shot19.enable()
        self.advance_time_and_run(.1)

        # show should still be at the same step
        self.assertLightColor("led_19", 'yellow')

        # but it should also still be running
        self.advance_time_and_run(1)
        self.assertLightColor("led_19", 'green')

        # hit the shot
        shot19.hit()
        self.advance_time_and_run(.1)

        # should switch to the second show
        self.assertLightColor("led_19", 'aliceblue')

        # and that show should be running
        self.advance_time_and_run()
        self.assertLightColor("led_19", 'antiquewhite')

        # disable the shot
        shot19.disable()
        self.advance_time_and_run(.1)

        # color should not change
        self.assertLightColor("led_19", 'antiquewhite')

        # and show should still be running
        self.advance_time_and_run(1)
        self.assertLightColor("led_19", 'aquamarine')

    def test_no_show_when_disabled(self):
        shot20 = self.machine.shots["shot_20"]

        self.start_game()

        # shot20 should be disabled
        self.assertFalse(shot20.enabled)

        # make sure the show is not running and not affecting the LED
        self.assertLightColor("led_20", 'off')

        # enable the shot, show should start
        shot20.enable()

        self.assertFalse(shot20.config['profile'].config['show_when_disabled'])
        self.assertTrue(shot20.enabled)

        self.advance_time_and_run(.1)
        self.assertLightColor("led_20", 'red')

        # make sure show is advancing
        self.advance_time_and_run(1)
        self.assertLightColor("led_20", 'orange')

        # hit the shot, show should switch
        shot20.hit()
        self.advance_time_and_run(.1)

        self.assertLightColor("led_20", 'aliceblue')

        # and that show should be running
        self.advance_time_and_run()
        self.assertLightColor("led_20", 'antiquewhite')

        # disable the shot
        shot20.disable()
        self.advance_time_and_run()

        # LEDs should be off since show_when_disabled == false
        self.assertLightColor("led_20", 'off')

    def test_hold_true(self):
        self.start_game()
        self.assertLightColor("led_24", 'orange')

        # advance the time past the end of the show and make sure that the
        # led is still on
        # all these separate entries are needed due to the way the tests run
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertLightColor("led_24", 'purple')

    def test_hold_false(self):
        self.start_game()
        self.assertLightColor("led_25", 'orange')

        # advance the time past the end of the show and make sure that the
        # led is off
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.advance_time_and_run(1)
        self.assertLightColor("led_25", 'off')

    def test_show_restore_in_mode(self):
        self.start_game()

        self.assertLightColor("led_27", "black")

        self.machine.modes["mode2"].start()
        self.advance_time_and_run()

        # step1 red
        self.assertLightColor("led_27", "red")

        self.hit_and_release_switch("switch_27")
        self.advance_time_and_run()

        # step2 orange
        self.assertLightColor("led_27", "orange")

        self.machine.modes["mode2"].stop()
        self.advance_time_and_run()

        # mode stopped. led off
        self.assertLightColor("led_27", "black")

        self.machine.modes["mode2"].start()
        self.advance_time_and_run()

        # back to step2. orange
        self.assertLightColor("led_27", "orange")

        self.hit_and_release_switch("switch_27")
        self.advance_time_and_run()

        # step3
        self.assertLightColor("led_27", "yellow")

    def test_show_restore_in_mode_start_step(self):
        # same as previous test but with a profile with start steps
        self.start_game()

        self.assertLightColor("led_28", "black")

        self.machine.modes["mode2"].start()
        self.advance_time_and_run()
        self.assertTrue(self.machine.shots["mode2_shot_rainbow_start_step"].enabled)

        # step1 red
        self.assertLightColor("led_28", "red")
        self.assertEqual("red", self.machine.shots["mode2_shot_rainbow_start_step"].state_name)

        self.hit_and_release_switch("switch_28")
        self.advance_time_and_run()

        # step2 orange
        self.assertLightColor("led_28", "orange")
        self.assertEqual("orange", self.machine.shots["mode2_shot_rainbow_start_step"].state_name)

        self.machine.modes["mode2"].stop()
        self.advance_time_and_run()

        # mode stopped. led off
        self.assertLightColor("led_28", "black")
        self.assertFalse(self.machine.shots["mode2_shot_rainbow_start_step"].enabled)

        self.machine.modes["mode2"].start()
        self.advance_time_and_run()

        # back to step2. orange
        self.assertEqual("orange", self.machine.shots["mode2_shot_rainbow_start_step"].state_name)
        self.assertLightColor("led_28", "orange")
        self.assertTrue(self.machine.shots["mode2_shot_rainbow_start_step"].enabled)

        self.hit_and_release_switch("switch_28")
        self.advance_time_and_run()

        # step3
        self.assertEqual("yellow", self.machine.shots["mode2_shot_rainbow_start_step"].state_name)
        self.assertLightColor("led_28", "yellow")

    def test_show_tokens_in_shot(self):
        """Test show tokens in shots and shot_profiles."""
        self.start_game()
        self.machine.modes["mode2"].start()

        self.assertLightColor("led_29", "black")

        # make sure nothing crashes when variables are missing
        self.post_event("mode2_shot_show_tokens_enable")
        self.assertLightColor("led_29", "black")
        self.assertEqual("one", self.machine.shots["mode2_shot_show_tokens"].state_name)

        self.post_event("mode2_shot_show_tokens_advance")
        self.assertLightColor("led_29", "black")
        self.assertEqual("two", self.machine.shots["mode2_shot_show_tokens"].state_name)

        # set variables
        self.machine.variables.set_machine_var("leds", "led_29")
        self.machine.variables.set_machine_var("color1", "red")
        self.machine.variables.set_machine_var("color2", "green")
        self.machine.variables.set_machine_var("color3", "blue")

        # try again
        self.post_event("mode2_shot_show_tokens_reset")

        self.assertLightColor("led_29", "red")
        self.assertEqual("one", self.machine.shots["mode2_shot_show_tokens"].state_name)

        self.post_event("mode2_shot_show_tokens_advance")
        self.assertLightColor("led_29", "green")
        self.assertEqual("two", self.machine.shots["mode2_shot_show_tokens"].state_name)

        self.post_event("mode2_shot_show_tokens_advance")
        self.assertLightColor("led_29", "blue")
        self.assertEqual("three", self.machine.shots["mode2_shot_show_tokens"].state_name)

    def test_jump(self):
        """Test jumping shots and shot_profiles."""
        self.start_game()
        self.machine.modes["mode2"].start()
        shot = self.machine.device_manager.collections["shots"]["mode2_shot_changing_profile"]

        # Initial color of the light for this profile
        self.assertLightColor("led_20", "yellow")

        # Change the profile and jump without force_show
        shot.config['profile'] = self.machine.device_manager.collections["shot_profiles"]['changing_profile_two']
        shot.jump(0)
        # State is the same, no color change
        self.assertLightColor("led_20", "yellow")

        # Jump and force_show
        shot.jump(0, True, True)
        # Should see the color of the new profile at the same state
        self.assertLightColor("led_20", "purple")
