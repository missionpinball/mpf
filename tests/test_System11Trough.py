import unittest

from mpf.system.machine import MachineController
from MpfTestCase import MpfTestCase
from mock import MagicMock
import time

class TestSystem11Trough(MpfTestCase):

    def getConfigFile(self):
        return 'test_system_11_trough.yaml'

    def getMachinePath(self):
        return '../tests/machine_files/ball_device/'

    def test_boot_with_ball_in_drain_empty_trough(self):
        # MPF starts with a ball in the outhole (drain device). It should be
        # ejected into the trough and stay there.
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.machine.switch_controller.process_switch("outhole", 1)
        self.advance_time_and_run(.6)

        self.assertEquals(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEquals(0, self.machine.coils.trough.pulse.call_count)

        self.machine.switch_controller.process_switch("outhole", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("trough3", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, self.machine.ball_devices.outhole.balls)
        self.assertEquals(1, self.machine.ball_devices.trough.balls)
        self.assertEquals(0, self.machine.ball_devices.playfield.balls)
        self.assertEquals(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEquals(0, self.machine.coils.trough.pulse.call_count)
        self.assertEquals('idle', self.machine.ball_devices.outhole._state)
        self.assertEquals('idle', self.machine.ball_devices.trough._state)
        self.assertEquals('idle', self.machine.ball_devices.plunger._state)

    def test_boot_with_balls_in_drain_and_trough(self):
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.machine.switch_controller.process_switch("outhole", 1)
        self.machine.switch_controller.process_switch("trough1", 1)
        self.machine.switch_controller.process_switch("trough2", 1)
        self.advance_time_and_run(.6)

        self.assertEquals(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEquals(0, self.machine.coils.trough.pulse.call_count)

        self.machine.switch_controller.process_switch("outhole", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("trough3", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, self.machine.ball_devices.outhole.balls)
        self.assertEquals(3, self.machine.ball_devices.trough.balls)
        self.assertEquals(0, self.machine.ball_devices.playfield.balls)
        self.assertEquals(1, self.machine.coils.outhole.pulse.call_count)
        self.assertEquals(0, self.machine.coils.trough.pulse.call_count)
        self.assertEquals('idle', self.machine.ball_devices.outhole._state)
        self.assertEquals('idle', self.machine.ball_devices.trough._state)
        self.assertEquals('idle', self.machine.ball_devices.plunger._state)

    def test_add_ball_to_pf(self):
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.machine.switch_controller.process_switch("trough1", 1)
        self.machine.switch_controller.process_switch("trough2", 1)
        self.machine.switch_controller.process_switch("trough3", 1)
        self.advance_time_and_run(1)

        self.assertEquals(0, self.machine.coils.outhole.pulse.call_count)
        self.assertEquals(0, self.machine.coils.trough.pulse.call_count)
        self.assertEquals(0, self.machine.ball_devices.outhole.balls)
        self.assertEquals(3, self.machine.ball_devices.trough.balls)
        self.assertEquals(0, self.machine.ball_devices.playfield.balls)
        self.assertEquals('idle', self.machine.ball_devices.outhole._state)
        self.assertEquals('idle', self.machine.ball_devices.trough._state)
        self.assertEquals('idle', self.machine.ball_devices.plunger._state)

        self.machine.playfield.add_ball(player_controlled=True)
        self.advance_time_and_run(1)

        self.assertEquals(1, self.machine.coils.trough.pulse.call_count)
        self.machine.switch_controller.process_switch("trough1", 0)
        self.advance_time_and_run(.1)

        self.machine.switch_controller.process_switch("plunger", 1)

        self.advance_time_and_run(1)

        self.assertEquals('idle', self.machine.ball_devices.outhole._state)
        self.assertEquals('idle', self.machine.ball_devices.trough._state)
        self.assertEquals('ejecting', self.machine.ball_devices.plunger._state)
        # self.assertEquals(1,
        #                   self.machine.ball_devices.playfield.num_balls_requested)

        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)

    def test_boot_and_start_game_with_ball_in_plunger(self):
        self.machine.coils.outhole.pulse = MagicMock()
        self.machine.coils.trough.pulse = MagicMock()

        self.machine.ball_controller.num_balls_known = 3
        self.machine.switch_controller.process_switch("plunger", 1)
        self.machine.switch_controller.process_switch("trough1", 1)
        self.machine.switch_controller.process_switch("trough2", 1)
        self.advance_time_and_run(.6)

        self.assertEquals(0, self.machine.ball_devices.outhole.balls)
        self.assertEquals(2, self.machine.ball_devices.trough.balls)
        self.assertEquals(1, self.machine.ball_devices.plunger.balls)
        self.assertEquals(0, self.machine.ball_devices.playfield.balls)
        self.assertEquals('idle', self.machine.ball_devices.outhole._state)
        self.assertEquals('idle', self.machine.ball_devices.trough._state)
        self.assertEquals('ejecting', self.machine.ball_devices.plunger._state)

        self.machine.switch_controller.process_switch("start", 1)
        self.machine.switch_controller.process_switch("start", 0)
        self.advance_time_and_run(1)

        self.assertIsNotNone(self.machine.game)
        self.assertEquals(0, self.machine.coils.trough.pulse.call_count)

        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("plunger", 0)
        self.advance_time_and_run(1)
        self.assertEquals(0, self.machine.coils.trough.pulse.call_count)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)
        self.machine.switch_controller.process_switch("playfield", 1)
        self.machine.switch_controller.process_switch("playfield", 0)
        self.advance_time_and_run(1)

        self.assertEquals(0, self.machine.ball_devices.outhole.balls)
        self.assertEquals(2, self.machine.ball_devices.trough.balls)
        self.assertEquals(0, self.machine.ball_devices.plunger.balls)
        self.assertEquals(1, self.machine.ball_devices.playfield.balls)
        self.assertEquals('idle', self.machine.ball_devices.outhole._state)
        self.assertEquals('idle', self.machine.ball_devices.trough._state)
        self.assertEquals('idle', self.machine.ball_devices.plunger._state)

        self.machine.switch_controller.process_switch("outhole", 1)
        self.advance_time_and_run(.6)

        self.assertEquals(2, self.machine.game.player.ball)
        self.assertEquals(1, self.machine.coils.trough.pulse.call_count)
        self.machine.switch_controller.process_switch("trough2", 0)
        self.advance_time_and_run(.1)
        self.machine.switch_controller.process_switch("plunger", 1)
        self.advance_time_and_run(.6)
        self.assertEquals(1, self.machine.coils.outhole.pulse.call_count)
        self.machine.switch_controller.process_switch("outhole", 0)
        self.machine.switch_controller.process_switch("trough2", 1)
        self.advance_time_and_run(1)

        self.assertEquals('idle', self.machine.ball_devices.outhole._state)
        self.assertEquals('idle', self.machine.ball_devices.trough._state)
        self.assertEquals('ejecting', self.machine.ball_devices.plunger._state)
