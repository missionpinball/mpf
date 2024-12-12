"""Test gottlieb trough setup with system11 trough + drain device."""
from mpf.tests.MpfTestCase import MpfTestCase, test_config
from unittest.mock import MagicMock


class TestGottliebTrough(MpfTestCase):

    """Test Gottlieb style troughs with outhole and only one one or two switches."""

    def get_config_file(self):
        return 'test_gottlieb_trough.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_boot_with_ball_in_drain_empty_trough(self):
        # MPF starts with a ball in the outhole (drain device). It should be
        # ejected into the trough and stay there.
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.hit_switch_and_run("outhole", 0.6)

        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)

        self.release_switch_and_run("outhole", 1)

        self.hit_and_release_switch("trough_entry")
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(1, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

    @test_config("test_gottlieb_trough_with_initial_balls.yaml")
    def test_boot_with_balls_in_drain_and_trough(self):
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.hit_switch_and_run("outhole", 1)
        self.advance_time_and_run(.6)

        # trough is full. there should be no eject
        self.assertEqual(0, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)

        self.assertEqual(1, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertNumBallsKnown(4)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(0, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        # self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

        # start game
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertIsNotNone(self.machine.game)
        self.assertEqual(0, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(1, self.machine.coils["trough"].pulse.call_count)

        # now the trough has space and the outhole can eject
        self.release_switch_and_run("trough_entry", 7)
        self.assertEqual(0, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(1, self.machine.coils["trough"].pulse.call_count)

        self.hit_switch_and_run("plunger", 1)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(1, self.machine.coils["trough"].pulse.call_count)

        self.release_switch_and_run("outhole", 1)
        self.release_switch_and_run("plunger", 1)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(1, self.machine.coils["trough"].pulse.call_count)

        self.hit_switch_and_run("trough_entry", 4)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)

        # ball drains
        self.hit_switch_and_run("outhole", 1)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(2, self.machine.coils["trough"].pulse.call_count)

        self.machine.log.warning("TEST: DRAIN")

        # we usually see the ball in the plunger first
        self.hit_switch_and_run("plunger", 1)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(2, self.machine.coils["trough"].pulse.call_count)

        # about a second later the trough switch deactives
        self.release_switch_and_run("trough_entry", 1)
        self.assertEqual(2, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(2, self.machine.coils["trough"].pulse.call_count)

        self.release_switch_and_run("outhole", 1)
        self.hit_switch_and_run("trough_entry", 1)

        self.release_switch_and_run("plunger", 10)
        self.assertEqual(2, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(2, self.machine.coils["trough"].pulse.call_count)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

    @test_config("test_gottlieb_trough_with_initial_balls.yaml")
    def test_add_ball_to_pf(self):
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.assertEqual(0, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.assertEqual(1, self.machine.coils["trough"].pulse.call_count)
        self.advance_time_and_run(.1)
        # simulate some bouncing on the switch on eject
        self.release_switch_and_run("trough_entry", 1)
        self.hit_switch_and_run("trough_entry", .3)
        self.release_switch_and_run("trough_entry", .6)

        self.machine.switch_controller.process_switch("plunger", 1)

        self.advance_time_and_run(1)

        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('ejecting', self.machine.ball_devices["plunger"]._state)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(1, self.machine.ball_devices["playfield"].num_balls_requested)
        self.machine.switch_controller.process_switch("plunger", 0)

        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

        self.assertEqual(0, self.machine.ball_devices["playfield"].num_balls_requested)
        self.assertEqual(1, self.machine.ball_devices["playfield"].balls)

    @test_config("test_gottlieb_trough_with_initial_balls.yaml")
    def test_boot_and_start_game_with_ball_in_plunger(self):
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(.6)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(1, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('ejecting', self.machine.ball_devices["plunger"]._state)

        # should not start
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertIsNone(self.machine.game)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)

        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(1, self.machine.ball_devices["playfield"].balls)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

        self.hit_switch_and_run("outhole", 1)

        # self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

        # game should start now
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertIsNotNone(self.machine.game)
        self.assertEqual(1, self.machine.coils["trough"].pulse.call_count)
        self.release_switch_and_run("trough_entry", 1)

        self.advance_time_and_run(.1)
        self.hit_switch_and_run("plunger", 1)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.release_switch_and_run("outhole", 1)
        self.hit_switch_and_run("trough_entry", 4)

        self.assertEqual(4, self.machine.ball_controller.num_balls_known)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('ejecting', self.machine.ball_devices["plunger"]._state)

        self.release_switch_and_run("plunger", 10)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

    def test_boot_with_two_balls_in_trough(self):
        # two balls are in trough
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        # but mpf does not know and assumes 0 in trough
        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(0, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(0, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

        # starting a game should fail
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertIsNone(self.machine.game)

        # a ball is added in while machine is running
        self.hit_switch_and_run("outhole", 1)

        self.assertEqual(1, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(0, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertEqual('ejecting', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

        # outhole ejects and ball enters trough
        self.release_switch_and_run("outhole", 1)
        # ball three sits on entrance switch
        self.hit_switch_and_run("trough_entry", 4)

        # trough recognizes that its actually full
        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        # game should now start
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertIsNotNone(self.machine.game)

    def test_single_ball_drain_and_eject(self):
        # tests that when a ball drains into the outhole and is in the process
        # of being ejected to the trough, MPF is able to also request a ball
        # to the plunger even though the ball hasn't made it into the trough
        # yet

        self.machine.ball_devices["trough"].ball_count_handler.counter._last_count = 3
        self.machine.ball_devices["trough"].available_balls = 3
        self.machine.ball_controller.num_balls_known = 3
        self.machine.ball_devices["trough"].ball_count_handler._set_ball_count(3)
        self.advance_time_and_run(1)

        self.machine.coils["trough"].pulse = MagicMock()

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)

        # start a game, ball goes to plunger
        self.hit_and_release_switch("start")
        self.advance_time_and_run(5)
        self.assertIsNotNone(self.machine.game)

        self.machine.playfield.add_ball()
        self.machine.playfield.add_ball()

        self.assertEqual(1, self.machine.coils["trough"].pulse.call_count)

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(2)

        # plunge to playfield
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(2)

        self.assertEqual(2, self.machine.coils["trough"].pulse.call_count)

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(2)

        # plunge to playfield
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(3)

        self.assertEqual(3, self.machine.coils["trough"].pulse.call_count)

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(2)

        # plunge to playfield
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(3)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(0, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(3, self.machine.ball_devices["playfield"].balls)

        # drain
        self.machine.switch_controller.process_switch("outhole", 1)
        self.advance_time_and_run(.6)
        self.assertEqual(2, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(2, self.machine.game.player.ball)

        self.machine.switch_controller.process_switch("outhole", 0)
        self.advance_time_and_run(.1)

    @test_config("test_gottlieb_trough_with_initial_balls.yaml")
    def test_drain_during_game_start(self):
        # A ball drains shortly after game start
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.hit_switch_and_run("start", 0.15)
        self.release_switch_and_run("start", 0.73)
        self.hit_switch_and_run("playfield", 0.123)
        self.release_switch_and_run("playfield", 0.325)
        self.hit_switch_and_run("outhole", 0.448)
        self.hit_switch_and_run("plunger", 0.4)     # this was originally 0.888s. will cause a new ball when > 0.5s
        self.release_switch_and_run("trough_entry", 3.244)
        self.release_switch_and_run("plunger", 0.322)
        self.hit_and_release_switch("playfield")
        self.advance_time_and_run(20)

        self.assertEqual(4, self.machine.ball_controller.num_balls_known)

        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

    @test_config("test_gottlieb_trough_with_initial_balls.yaml")
    def test_double_drain_during_trough_eject(self):
        self.mock_event("balldevice_outhole_ball_eject_failed")
        self.mock_event("balldevice_ball_missing")
        self.machine.ball_devices["plunger"].config['eject_timeouts'][self.machine.playfield] = 20000
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        self.machine.ball_controller.num_balls_known = 7
        self.machine.playfield.available_balls = 3
        self.machine.playfield.balls = 3

        self.assertEqual(7, self.machine.ball_controller.num_balls_known)

        self.machine.playfield.add_ball(1)
        self.advance_time_and_run(1)

        self.release_switch_and_run("trough_entry", .5)
        self.hit_switch_and_run("plunger", 1)
        self.release_switch_and_run("plunger", 3)

        # make sure the eject does not fail when the trough has scheduled an eject
        self.machine.playfield.add_ball(1)

        self.hit_switch_and_run("outhole", 1)
        self.release_switch_and_run("outhole", 1)
        # a new ball enters outhole from the playfield
        self.hit_switch_and_run("outhole", 0)
        self.hit_switch_and_run("trough_entry", 4)
        self.advance_time_and_run(4)
        self.assertEventNotCalled("balldevice_outhole_ball_eject_failed")
        self.assertEventNotCalled("balldevice_ball_missing")

    @test_config("test_gottlieb_trough_with_initial_balls.yaml")
    def test_eject_during_incoming_ball(self):
        self.mock_event("balldevice_outhole_ball_eject_failed")
        self.mock_event("balldevice_ball_missing")
        self.machine.ball_devices["plunger"].config['eject_timeouts'][self.machine.playfield] = 20000
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()
        self.assertEqual(3, self.machine.ball_controller.num_balls_known)

        self.machine.ball_controller.num_balls_known = 7
        self.machine.playfield.available_balls = 3
        self.machine.playfield.balls = 3

        self.assertEqual(7, self.machine.ball_controller.num_balls_known)

        self.machine.playfield.add_ball(1)
        self.advance_time_and_run(1)

        self.release_switch_and_run("trough_entry", .5)
        self.hit_switch_and_run("plunger", 1)
        self.release_switch_and_run("plunger", 30)

        # a ball drains
        self.hit_switch_and_run("outhole", 1)
        self.release_switch_and_run("outhole", 1)

        # another ball enters the outhole
        self.hit_switch_and_run("outhole", 0)
        # and the trough gets an eject request
        self.machine.playfield.add_ball(1)
        self.advance_time_and_run()
        self.hit_and_release_switch("trough_entry")
        # this goed beyond the timeout of the outhole
        self.advance_time_and_run(6)
        # a new ball enters outhole from the playfield
        self.hit_switch_and_run("plunger", 1)
        self.release_switch_and_run("plunger", 1)

        self.assertEventNotCalled("balldevice_outhole_ball_eject_failed")
        self.assertEventNotCalled("balldevice_ball_missing")
