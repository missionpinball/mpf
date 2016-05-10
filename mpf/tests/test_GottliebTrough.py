from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestGottliebTrough(MpfTestCase):

    def getConfigFile(self):
        if (self._testMethodName == "test_boot_with_balls_in_drain_and_trough" or
                self._testMethodName == "test_add_ball_to_pf" or
                self._testMethodName == "test_boot_and_start_game_with_ball_in_plunger"):
            return 'test_gottlieb_trough_with_initial_balls.yaml'
        else:
            return 'test_gottlieb_trough.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/ball_device/'

    def test_boot_with_ball_in_drain_empty_trough(self):
        # MPF starts with a ball in the outhole (drain device). It should be
        # ejected into the trough and stay there.
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.hit_switch_and_run("outhole", 0.6)

        self.assertEqual(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)

        self.release_switch_and_run("outhole", 1)

        self.hit_and_release_switch("trough_entry")
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(1, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)

    def test_boot_with_balls_in_drain_and_trough(self):
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.hit_switch_and_run("outhole", 1)
        self.advance_time_and_run(.6)

        # trough is full. there should be no eject
        self.assertEqual(0, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)

        self.assertEqual(1, self.machine.ball_devices.outhole.balls)
        self.assertEqual(3, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual(0, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.assertEqual('wait_for_eject', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)

        # start game
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertIsNotNone(self.machine.game)
        self.assertEqual(0, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(1, self.machine.coils.trough.pulse.call_count)

        # now the trough has space and the outhole can eject
        self.release_switch_and_run("trough_entry", 0)
        self.hit_switch_and_run("plunger", 1)
        self.assertEqual(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(1, self.machine.coils.trough.pulse.call_count)

        self.release_switch_and_run("plunger", 0)
        self.release_switch_and_run("outhole", 1)

        self.hit_and_release_switch("trough_entry")
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(3, self.machine.ball_devices.trough.balls)

    def test_add_ball_to_pf(self):
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.assertEqual(0, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(3, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual('idle', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.assertEqual(1, self.machine.coils.trough.pulse.call_count)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.process_switch("plunger", 1)

        self.advance_time_and_run(1)

        self.assertEqual('idle', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('ejecting', self.machine.ball_devices.plunger._state)
        # self.assertEquals(1,
        #                   self.machine.ball_devices.playfield.num_balls_requested)

        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)

    def test_boot_and_start_game_with_ball_in_plunger(self):
        self.machine.ball_controller.num_balls_known = 0
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(.6)

        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(3, self.machine.ball_devices.trough.balls)
        self.assertEqual(1, self.machine.ball_devices.plunger.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual('idle', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('ejecting', self.machine.ball_devices.plunger._state)

        # should not start
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertIsNone(self.machine.game)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)

        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(3, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.plunger.balls)
        self.assertEqual(1, self.machine.ball_devices.playfield.balls)
        self.assertEqual('idle', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)

        self.hit_switch_and_run("outhole", 1)

        self.assertEqual('wait_for_eject', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)

        # game should start now
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertIsNotNone(self.machine.game)
        self.assertEqual(1, self.machine.coils.trough.pulse.call_count)

        self.advance_time_and_run(.1)
        self.hit_switch_and_run("plunger", 1)
        self.assertEqual(1, self.machine.coils.outhole.pulse.call_count)
        self.release_switch_and_run("outhole", 1)
        self.hit_and_release_switch("trough_entry")
        self.advance_time_and_run(1)

        self.assertEqual('ball_left', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('ejecting', self.machine.ball_devices.plunger._state)

    def test_boot_with_two_balls_in_trough(self):
        # two balls are in trough
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        # but mpf does not know and assumes 0 in trough
        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(0, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual(0, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)

        # starting a game should fail
        self.hit_and_release_switch("start")
        self.advance_time_and_run(1)
        self.assertEqual(0, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.assertIsNone(self.machine.game)

        # a ball is added in while machine is running
        self.hit_switch_and_run("outhole", 1)

        self.assertEqual(1, self.machine.ball_devices.outhole.balls)
        self.assertEqual(0, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.assertEqual('ejecting', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)

        # outhole ejects and ball enters trough
        self.release_switch_and_run("outhole", 1)
        # ball three sits on entrance switch
        self.hit_switch_and_run("trough_entry", 4)

        # trough recognizes that its actually full
        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(3, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)
        self.assertEqual(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEqual(0, self.machine.coils.trough.pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices.outhole._state)
        self.assertEqual('idle', self.machine.ball_devices.trough._state)
        self.assertEqual('idle', self.machine.ball_devices.plunger._state)
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

        self.machine.ball_devices.trough.balls = 3
        self.machine.ball_devices.trough.available_balls = 3
        self.machine.ball_controller.num_balls_known = 3
        self.advance_time_and_run(1)

        self.machine.coils.trough.pulse = MagicMock()

        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(3, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.plunger.balls)
        self.assertEqual(0, self.machine.ball_devices.playfield.balls)

        # start a game, ball goes to plunger
        self.hit_and_release_switch("start")
        self.advance_time_and_run(5)
        self.assertIsNotNone(self.machine.game)

        self.machine.playfield.add_ball()
        self.machine.playfield.add_ball()

        self.assertEqual(1, self.machine.coils.trough.pulse.call_count)

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(2)

        # plunge to playfield
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(2)

        self.assertEqual(2, self.machine.coils.trough.pulse.call_count)

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(2)

        # plunge to playfield
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(2)

        self.assertEqual(3, self.machine.coils.trough.pulse.call_count)

        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(2)

        # plunge to playfield
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(2)

        self.assertEqual(0, self.machine.ball_devices.outhole.balls)
        self.assertEqual(0, self.machine.ball_devices.trough.balls)
        self.assertEqual(0, self.machine.ball_devices.plunger.balls)
        self.assertEqual(3, self.machine.ball_devices.playfield.balls)

        # drain
        self.machine.switch_controller.process_switch("outhole", 1)
        self.advance_time_and_run(.6)
        self.assertEqual(2, self.machine.ball_devices.playfield.balls)
        self.assertEqual(2, self.machine.game.player.ball)

        self.machine.switch_controller.process_switch("outhole", 0)
        self.advance_time_and_run(.1)
