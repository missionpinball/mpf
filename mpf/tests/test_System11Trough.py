from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestSystem11Trough(MpfTestCase):

    def get_config_file(self):
        return 'test_system_11_trough.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_boot_with_ball_in_drain_empty_trough(self):
        # MPF starts with a ball in the outhole (drain device). It should be
        # ejected into the trough and stay there.
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.machine.switch_controller.process_switch("outhole", 1)
        self.advance_time_and_run(.6)

        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)

        self.machine.switch_controller.process_switch("outhole", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("trough3", 1)
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(1, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

    def test_boot_with_balls_in_drain_and_trough(self):
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.machine.switch_controller.process_switch("outhole", 1)
        self.machine.switch_controller.process_switch("trough1", 1)
        self.machine.switch_controller.process_switch("trough2", 1)
        self.advance_time_and_run(.6)

        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)

        self.machine.switch_controller.process_switch("outhole", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("trough3", 1)
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(1, self.machine.coils["outhole"].pulse.call_count)
        self.assertEqual(0, self.machine.coils["trough"].pulse.call_count)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)

    def test_add_ball_to_pf(self):
        self.machine.coils["outhole"].pulse = MagicMock()
        self.machine.coils["trough"].pulse = MagicMock()

        self.machine.switch_controller.process_switch("trough1", 1)
        self.machine.switch_controller.process_switch("trough2", 1)
        self.machine.switch_controller.process_switch("trough3", 1)
        self.advance_time_and_run(1)

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
        self.machine.switch_controller.process_switch("trough1", 0)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.process_switch("plunger", 1)

        self.advance_time_and_run(1)

        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('ejecting', self.machine.ball_devices["plunger"]._state)
        # self.assertEquals(1,
        #                   self.machine.ball_devices["playfield"].num_balls_requested)

        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)

    def test_single_ball_drain_and_eject(self):
        # tests that when a ball drains into the outhole and is in the process
        # of being ejected to the trough, MPF is able to also request a ball
        # to the plunger even though the ball hasn't made it into the trough
        # yet

        self.machine.switch_controller.process_switch("trough1", 1)
        self.advance_time_and_run(1)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(1, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)

        # start a game, ball goes to plunger
        self.machine.switch_controller.process_switch("start", 1)
        self.machine.switch_controller.process_switch("start", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("trough1", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(2)

        self.assertIsNotNone(self.machine.game)

        # plunge to playfield
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(2)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(2)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(0, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(1, self.machine.ball_devices["playfield"].balls)

        # drain
        self.machine.switch_controller.process_switch("outhole", 1)
        self.advance_time_and_run(.6)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)
        self.assertEqual(2, self.machine.game.player.ball)

        self.machine.switch_controller.process_switch("outhole", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("trough1", 1)


class TestSystem11TroughStartup(MpfTestCase):

    def get_config_file(self):
        return 'test_system_11_trough_startup.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def get_platform(self):
        return "smart_virtual"

    def test_start_with_four_balls(self):
#        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)
        self.assertEqual(1, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(0, self.machine.ball_devices["outhole"].available_balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(4, self.machine.ball_devices["trough"].available_balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(0, self.machine.ball_devices["playfield"].balls)

        self.hit_and_release_switch("start")
        self.advance_time_and_run(20)
        self.release_switch_and_run("plunger", 10)

        self.assertEqual(0, self.machine.ball_devices["outhole"].balls)
        self.assertEqual(3, self.machine.ball_devices["trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["plunger"].balls)
        self.assertEqual(1, self.machine.ball_devices["playfield"].balls)
        self.assertEqual('idle', self.machine.ball_devices["outhole"]._state)
        self.assertEqual('idle', self.machine.ball_devices["trough"]._state)
        self.assertEqual('idle', self.machine.ball_devices["plunger"]._state)
