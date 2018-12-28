from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestExtraBall(MpfGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/extra_ball/'

    def get_platform(self):
        return 'smart_virtual'

    def test_extra_ball(self):
        # tests basic EB functionality and also max_per_game setting
        self.mock_event('extra_ball_awarded')
        self.mock_event('extra_ball_eb1_awarded')
        self.mock_event('extra_ball_award_disabled')
        self.mock_event('extra_ball_eb1_award_disabled')
        self.mock_event("first_ball")

        self.fill_troughs()
        self.start_game()

        self.assertEventCalled("first_ball")
        self.mock_event("first_ball")

        # start mode
        self.post_event("start_mode1")

        # mode loaded. eb1 should be enabled
        self.assertTrue(self.machine.extra_balls.eb1)
        self.assertTrue(self.machine.extra_balls.eb1.player)
        self.assertTrue(self.machine.extra_balls.eb1.enabled)
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(0, self.machine.game.player.extra_ball_eb1_awarded)
        self.assertEqual(0, self.machine.game.player.extra_balls)

        # stop mode
        self.post_event("stop_mode1")

        # nothing should happen
        self.post_event("award_eb1")
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(0, self.machine.game.player.extra_ball_eb1_awarded)
        self.assertEqual(0, self.machine.game.player.extra_balls)
        self.assertFalse(self.machine.extra_balls.eb1.player)

        # start mode (again)
        self.post_event("start_mode1")

        self.assertTrue(self.machine.extra_balls.eb1)
        self.assertTrue(self.machine.extra_balls.eb1.player)
        self.assertTrue(self.machine.extra_balls.eb1.enabled)
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(0, self.machine.game.player.extra_ball_eb1_awarded)
        self.assertEqual(0, self.machine.game.player.extra_balls)

        # player gets extra_ball
        self.post_event("award_eb1")
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(1, self.machine.game.player.extra_ball_eb1_num_awarded)
        self.assertEqual(1, self.machine.game.player.extra_balls)
        self.assertEventCalled('extra_ball_awarded')
        self.assertEventCalled('extra_ball_eb1_awarded')
        self.assertEventNotCalled('extra_ball_award_disabled')
        self.assertEventNotCalled('extra_ball_eb1_award_disabled')

        # but only once
        self.assertFalse(self.machine.extra_balls.eb1.enabled)
        self.mock_event('extra_ball_awarded')
        self.mock_event('extra_ball_eb1_awarded')
        self.mock_event('extra_ball_award_disabled')
        self.mock_event('extra_ball_eb1_award_disabled')
        self.post_event("award_eb1")
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(1, self.machine.game.player.extra_ball_eb1_num_awarded)
        self.assertEqual(1, self.machine.game.player.extra_balls)
        self.assertEventNotCalled('extra_ball_awarded')
        self.assertEventNotCalled('extra_ball_eb1_awarded')
        self.assertEventCalled('extra_ball_award_disabled')
        self.assertEventCalled('extra_ball_eb1_award_disabled')

        # drain and start new ball, but should still be ball 1 since the player
        # has an EB
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEventNotCalled("first_ball")

        # EB disabled events should be posted
        self.mock_event('extra_ball_awarded')
        self.mock_event('extra_ball_eb1_awarded')
        self.mock_event('extra_ball_award_disabled')
        self.mock_event('extra_ball_eb1_award_disabled')
        self.post_event('start_mode1')
        self.post_event('award_eb1')
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(1, self.machine.game.player.extra_ball_eb1_num_awarded)
        self.assertEqual(0, self.machine.game.player.extra_balls)
        self.assertEventNotCalled('extra_ball_awarded')
        self.assertEventNotCalled('extra_ball_eb1_awarded')
        self.assertEventCalled('extra_ball_award_disabled')
        self.assertEventCalled('extra_ball_eb1_award_disabled')

    def test_extra_ball_disabled(self):
        self.mock_event('extra_ball_awarded')
        self.mock_event('extra_ball_eb3_awarded')
        self.mock_event('extra_ball_award_disabled')
        self.mock_event('extra_ball_eb3_award_disabled')

        self.fill_troughs()
        self.start_game()
        self.post_event("start_mode1")

        # mode loaded. eb3 should not be enabled
        self.assertTrue(self.machine.extra_balls.eb3)
        self.assertTrue(self.machine.extra_balls.eb3.player)
        self.assertFalse(self.machine.extra_balls.eb3.enabled)
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(0, self.machine.game.player.extra_ball_eb2_awarded)
        self.assertEqual(0, self.machine.game.player.extra_balls)

        # player gets extra_ball, but it's disabled
        self.post_event("award_eb3")
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEqual(1, self.machine.game.player.ball)
        self.assertEqual(0, self.machine.game.player.extra_ball_eb3_num_awarded)
        self.assertEqual(0, self.machine.game.player.extra_balls)
        self.assertEventNotCalled('extra_ball_awarded')
        self.assertEventNotCalled('extra_ball_eb3_awarded')
        self.assertEventCalled('extra_ball_award_disabled')
        self.assertEventCalled('extra_ball_eb3_award_disabled')

    def test_extra_ball_lit_with_no_group(self):
        self.mock_event('extra_ball_eb2_lit')
        self.mock_event('extra_ball_eb2_awarded')

        self.fill_troughs()
        self.start_game()
        self.post_event('start_mode1')
        self.post_event('light_eb2')
        self.assertEventCalled('extra_ball_eb2_lit')
        self.assertEventNotCalled('extra_ball_eb2_awarded')

    def test_extra_ball_lit_with_no_group_disabled(self):
        self.mock_event('extra_ball_eb4_lit')
        self.mock_event('extra_ball_eb4_awarded')
        self.mock_event('extra_ball_award_disabled')
        self.mock_event('extra_ball_eb4_award_disabled')

        self.fill_troughs()
        self.start_game()
        self.post_event('start_mode1')
        self.post_event('light_eb4')
        self.assertEventNotCalled('extra_ball_eb4_lit')
        self.assertEventNotCalled('extra_ball_eb4_awarded')
        self.assertEventCalled('extra_ball_award_disabled')
        self.assertEventCalled('extra_ball_eb4_award_disabled')

    def test_group(self):
        # tests basic group functionality
        self.fill_troughs()
        self.start_two_player_game()
        self.post_event('start_mode1')

        self.assertEqual(self.machine.extra_balls.eb5.group,
                         self.machine.extra_ball_groups.main)
        self.assertEqual(self.machine.extra_balls.eb6.group,
                         self.machine.extra_ball_groups.main)

        # award a group EB, even though none are lit
        self.mock_event('extra_ball_group_main_awarded')

        self.post_event('award_group_eb')
        self.assertEqual(1, self.machine.game.player.extra_balls)
        self.assertEqual(
            0, self.machine.game.player.extra_ball_group_main_num_lit)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_game)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_ball)
        self.assertEventCalled('extra_ball_group_main_awarded')

        # light single EB, make sure it works and the group vars update
        self.mock_event('extra_ball_group_main_lit')
        self.mock_event('extra_ball_group_main_lit_awarded')
        self.mock_event('extra_ball_group_main_awarded')

        self.post_event('light_eb5')
        self.assertEventCalled('extra_ball_group_main_lit')
        self.assertEventCalled('extra_ball_group_main_lit_awarded')
        self.assertEqual(1, self.machine.game.player.extra_balls)
        self.assertEqual(1,
            self.machine.game.player.extra_ball_group_main_num_lit)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_game)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_ball)

        # light another EB, but max lit for the group is 1, so it should not
        # light, and we should get the disabled event
        self.mock_event('extra_ball_group_main_lit')
        self.mock_event('extra_ball_group_main_lit_awarded')
        self.mock_event('extra_ball_group_main_awarded')
        self.mock_event('extra_ball_group_main_award_disabled')

        self.post_event('light_eb6')
        self.assertEventNotCalled('extra_ball_group_main_lit')
        self.assertEventNotCalled('extra_ball_group_main_lit_awarded')
        self.assertEventNotCalled('extra_ball_group_main_awarded')
        self.assertEventCalled('extra_ball_group_main_award_disabled')
        self.assertEqual(1, self.machine.game.player.extra_balls)
        self.assertEqual(1,
            self.machine.game.player.extra_ball_group_main_num_lit)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_game)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_ball)

        # drain the ball, player has EB so it should still be their turn
        # EB group should be lit from before
        self.mock_event('extra_ball_group_main_lit')
        self.mock_event('extra_ball_group_main_lit_awarded')

        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertEqual(1, self.machine.game.player.number)
        self.assertEventCalled('extra_ball_group_main_lit')
        self.assertEventNotCalled('extra_ball_group_main_lit_awarded')
        self.assertEqual(0, self.machine.game.player.extra_balls)
        self.assertEqual(1,
            self.machine.game.player.extra_ball_group_main_num_lit)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_game)
        self.assertEqual(1,
             self.machine.game.player.extra_ball_group_main_num_awarded_ball)

        # award another EB. This maxes out the extra balls they can get this
        # ball, so the lit one should unlight
        self.mock_event('extra_ball_group_main_awarded')
        self.mock_event('extra_ball_group_main_lit')
        self.mock_event('extra_ball_group_main_lit_awarded')
        self.mock_event('extra_ball_group_main_unlit')

        self.post_event('award_group_eb')
        self.assertEventNotCalled('extra_ball_group_main_lit')
        self.assertEventNotCalled('extra_ball_group_main_lit_awarded')
        self.assertEventCalled('extra_ball_group_main_awarded')
        self.assertEventCalled('extra_ball_group_main_unlit')
        self.assertEqual(1, self.machine.game.player.extra_balls)
        self.assertEqual(1,
            self.machine.game.player.extra_ball_group_main_num_lit)
        self.assertEqual(2,
             self.machine.game.player.extra_ball_group_main_num_awarded_game)
        self.assertEqual(2,
             self.machine.game.player.extra_ball_group_main_num_awarded_ball)

        # drain, should still be player 1 and the EB should still be lit
        self.mock_event('extra_ball_group_main_lit')
        self.mock_event('extra_ball_group_main_lit_awarded')

        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertEventCalled('extra_ball_group_main_lit')
        self.assertEventNotCalled('extra_ball_group_main_lit_awarded')
        self.assertEqual(0, self.machine.game.player.extra_balls)
        self.assertEqual(1,
            self.machine.game.player.extra_ball_group_main_num_lit)
        self.assertEqual(2,
             self.machine.game.player.extra_ball_group_main_num_awarded_game)
        self.assertEqual(2,
             self.machine.game.player.extra_ball_group_main_num_awarded_ball)

        # light another EB, but the max is 2 per ball, and even though this is
        # the next ball, it was an extra ball, so still Ball 1, so it should
        # not light
        self.mock_event('extra_ball_group_main_lit')
        self.mock_event('extra_ball_group_main_lit_awarded')
        self.mock_event('extra_ball_group_main_award_disabled')

        self.post_event('start_mode1')
        self.post_event('light_eb7')
        self.assertEventNotCalled('extra_ball_group_main_lit')
        self.assertEventNotCalled('extra_ball_group_main_lit_awarded')
        self.assertEventCalled('extra_ball_group_main_award_disabled')
        self.assertEqual(0, self.machine.game.player.extra_balls)
        self.assertEqual(1,
            self.machine.game.player.extra_ball_group_main_num_lit)
        self.assertEqual(2,
             self.machine.game.player.extra_ball_group_main_num_awarded_game)
        self.assertEqual(2,
             self.machine.game.player.extra_ball_group_main_num_awarded_ball)

        # drain and make sure we get to player 2
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.game.player.number)

    def test_group_disabled_with_eb_enabled(self):
        self.fill_troughs()
        self.start_game()
        self.post_event('start_mode1')

        self.mock_event('extra_ball_group_disabled_eb_lit')
        self.mock_event('extra_ball_group_disabled_eb_lit_awarded')
        self.mock_event('extra_ball_group_disabled_eb_award_disabled')

        self.post_event('light_eb8')
        self.assertEventNotCalled('extra_ball_group_disabled_eb_lit')
        self.assertEventNotCalled('extra_ball_group_disabled_eb_lit_awarded')
        self.assertEventCalled('extra_ball_group_disabled_eb_award_disabled')

        self.mock_event('extra_ball_group_disabled_eb_award_disabled')
        self.mock_event('extra_ball_group_disabled_eb_awarded')
        self.mock_event('extra_ball_eb8_award_disabled')
        self.mock_event('extra_ball_eb8_awarded')

        self.post_event('award_eb8')
        self.assertEventCalled('extra_ball_group_disabled_eb_award_disabled')
        self.assertEventNotCalled('extra_ball_group_disabled_eb_awarded')
        self.assertEventCalled('extra_ball_eb8_award_disabled')
        self.assertEventNotCalled('extra_ball_eb8_awarded')

        self.assertEqual(0, self.machine.game.player.extra_balls)

    def test_group_max_per_game(self):
        self.fill_troughs()
        self.start_game()
        self.post_event('start_mode1')
        self.post_event('award_eb9')
        self.post_event('award_eb9')
        self.post_event('award_eb9')
        self.assertEqual(2, self.machine.game.player.extra_balls)

    def test_lit_memory_false(self):
        self.mock_event('extra_ball_group_no_memory_lit')
        self.mock_event('extra_ball_group_no_memory_lit_awarded')

        # light EB, make sure it lights, but don't collect
        self.fill_troughs()
        self.start_game()
        self.post_event('start_mode1')
        self.post_event('light_eb9')
        self.assertEqual(1,
            self.machine.game.player.extra_ball_group_no_memory_num_lit)
        self.assertEventCalled('extra_ball_group_no_memory_lit')
        self.assertEventCalled('extra_ball_group_no_memory_lit_awarded')

        # drain and move to next ball, EB should be unlit
        self.mock_event('extra_ball_group_no_memory_lit')
        self.mock_event('extra_ball_group_no_memory_lit_awarded')
        self.drain_all_balls()
        self.advance_time_and_run()
        self.assertEqual(2, self.machine.game.player.ball)
        self.assertEqual(0,
            self.machine.game.player.extra_ball_group_no_memory_num_lit)
        self.assertEventNotCalled('extra_ball_group_no_memory_lit')
        self.assertEventNotCalled('extra_ball_group_no_memory_lit_awarded')
