from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestMagnet(MpfFakeGameTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/magnet/'

    def test_enable_on_game_start(self):
        self.assertFalse(self.machine.magnets["magnet_auto_enable"].enabled)
        self.mock_event("magnet_magnet_auto_enable_grabbing_ball")
        self.mock_event("magnet_magnet_auto_enable_grabbed_ball")
        self.assertEqual("disabled", self.machine.coils["magnet_coil3"].hw_driver.state)
        # hit switch
        self.hit_and_release_switch("grab_switch3")
        self.advance_time_and_run(.1)
        # magnet not enabled (game not started yet) -> nothing happens
        self.assertEqual("disabled", self.machine.coils["magnet_coil3"].hw_driver.state)
        # start game
        self.start_game()
        self.assertTrue(self.machine.magnets["magnet_auto_enable"].enabled)

        # try again
        self.hit_and_release_switch("grab_switch3")
        self.advance_time_and_run(.1)

        # magnet enables
        self.assertEventCalled("magnet_magnet_auto_enable_grabbing_ball")
        self.assertEventNotCalled("magnet_magnet_auto_enable_grabbed_ball")
        self.assertEqual("enabled", self.machine.coils["magnet_coil3"].hw_driver.state)

    def test_grab_and_release_and_fling(self):
        self.mock_event("magnet_magnet1_grabbing_ball")
        self.mock_event("magnet_magnet1_grabbed_ball")
        self.assertEqual("disabled", self.machine.coils["magnet_coil1"].hw_driver.state)
        # hit switch
        self.hit_and_release_switch("grab_switch1")
        self.advance_time_and_run(.1)
        # magnet not enabled -> nothing happens
        self.assertEqual("disabled", self.machine.coils["magnet_coil1"].hw_driver.state)
        # enable magnet and try again
        self.post_event("magnet1_enable")
        self.hit_and_release_switch("grab_switch1")
        self.advance_time_and_run(.1)

        # magnet enables
        self.assertEventCalled("magnet_magnet1_grabbing_ball")
        self.assertEventNotCalled("magnet_magnet1_grabbed_ball")
        self.assertEqual("enabled", self.machine.coils["magnet_coil1"].hw_driver.state)

        # success event after 1.5s
        self.advance_time_and_run(1.5)
        self.assertEventCalled("magnet_magnet1_grabbing_ball")
        self.assertEventCalled("magnet_magnet1_grabbed_ball")

        self.mock_event("magnet_magnet1_releasing_ball")
        self.mock_event("magnet_magnet1_released_ball")
        # release ball
        self.post_event("magnet1_release")
        self.advance_time_and_run(.1)
        # coil disables
        self.assertEqual("disabled", self.machine.coils["magnet_coil1"].hw_driver.state)
        self.assertEventCalled("magnet_magnet1_releasing_ball")
        self.assertEventNotCalled("magnet_magnet1_released_ball")

        # ball passes switch
        self.hit_and_release_switch("grab_switch1")

        # release done after .5s
        self.advance_time_and_run(.5)
        self.assertEventCalled("magnet_magnet1_releasing_ball")
        self.assertEventCalled("magnet_magnet1_released_ball")
        self.assertEqual("disabled", self.machine.coils["magnet_coil1"].hw_driver.state)

        # grab again
        self.mock_event("magnet_magnet1_grabbing_ball")
        self.mock_event("magnet_magnet1_grabbed_ball")
        self.hit_and_release_switch("grab_switch1")
        self.advance_time_and_run(.1)

        # magnet enables
        self.assertEventCalled("magnet_magnet1_grabbing_ball")
        self.assertEventNotCalled("magnet_magnet1_grabbed_ball")
        self.assertEqual("enabled", self.machine.coils["magnet_coil1"].hw_driver.state)

        # success event after 1.5s
        self.advance_time_and_run(1.5)
        self.assertEventCalled("magnet_magnet1_grabbing_ball")
        self.assertEventCalled("magnet_magnet1_grabbed_ball")

        # fling ball
        self.mock_event("magnet_magnet1_flinging_ball")
        self.mock_event("magnet_magnet1_flinged_ball")
        self.post_event("magnet1_fling")
        self.advance_time_and_run(.01)
        # coil disables
        self.assertEqual("disabled", self.machine.coils["magnet_coil1"].hw_driver.state)
        self.assertEventCalled("magnet_magnet1_flinging_ball")
        self.assertEventNotCalled("magnet_magnet1_flinged_ball")

        # coil reenables
        self.advance_time_and_run(.25)
        self.assertEqual("enabled", self.machine.coils["magnet_coil1"].hw_driver.state)
        self.assertEventCalled("magnet_magnet1_flinging_ball")
        self.assertEventNotCalled("magnet_magnet1_flinged_ball")

        # and disables again
        self.advance_time_and_run(.1)
        self.assertEqual("disabled", self.machine.coils["magnet_coil1"].hw_driver.state)
        self.assertEventCalled("magnet_magnet1_flinging_ball")
        self.assertEventCalled("magnet_magnet1_flinged_ball")

    def test_magnet_ball_save(self):
        # enable magnet ball save
        self.post_event("magnet_ball_save_enable")
        self.assertFalse(self.machine.ball_saves["magnet_save"].enabled)
        # ball passes flipper fingers and wants to drain
        self.hit_and_release_switch("grab_switch2")
        self.advance_time_and_run(.01)
        # but the magnet enables and saves it
        self.assertEqual("enabled", self.machine.coils["magnet_coil2"].hw_driver.state)
        self.assertTrue(self.machine.ball_saves["magnet_save"].enabled)
        # after 1.5s the magnet flings the ball up
        self.advance_time_and_run(1.5)
        self.assertEqual("disabled", self.machine.coils["magnet_coil2"].hw_driver.state)

        # coil reenables
        self.advance_time_and_run(.25)
        self.assertEqual("enabled", self.machine.coils["magnet_coil2"].hw_driver.state)

        # and disables again
        self.advance_time_and_run(.1)
        self.assertEqual("disabled", self.machine.coils["magnet_coil2"].hw_driver.state)

        # ball save stays enabled for a short moment in case the magnet missed it
        self.advance_time_and_run(3)
        self.assertTrue(self.machine.ball_saves["magnet_save"].enabled)

        # game continues and ball save times out
        self.advance_time_and_run(5)
        self.assertFalse(self.machine.ball_saves["magnet_save"].enabled)
