from mpf.tests.MpfTestCase import MpfTestCase
from unittest.mock import MagicMock


class TestDiverter(MpfTestCase):

    def getConfigFile(self):
        return self._testMethodName + ".yaml"

    def getMachinePath(self):
        return 'tests/machine_files/diverter/'

    def get_platform(self):
        return "smart_virtual"

    def start_game(self):
        # shots only work in games so we have to do this a lot
        self.machine.events.post('game_start')
        self.advance_time_and_run()
        self.machine.game.balls_in_play = 1
        self.assertIsNotNone(self.machine.game)

    def _block_device(self, queue, **kwargs):
        del kwargs
        self.queue = queue
        queue.wait()

    def test_delayed_eject(self):
        self.queue = None
        diverter = self.machine.diverters.d_test_delayed_eject

        self.machine.coils.c_diverter.enable = MagicMock()
        self.machine.coils.c_diverter.disable = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.events.add_handler("balldevice_test_trough_ball_eject_attempt", self._block_device)

        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_trough
        self.machine.playfield.add_ball()

        self.advance_time_and_run(20)
        self.queue.clear()

        self.advance_time_and_run(1)
        self.machine.events.remove_handler_by_event("balldevice_test_trough_ball_eject_attempt", self._block_device)

        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)
        self.machine.coils.c_diverter.enable.assert_called_once_with()
        self.machine.coils.c_diverter.enable = MagicMock()
        assert not self.machine.coils.c_diverter.disable.called

        self.advance_time_and_run(4)
        self.machine.coils.c_diverter.disable.assert_called_once_with()
        assert not self.machine.coils.c_diverter.enable.called

        self.hit_and_release_switch("s_playfield")
        self.machine_run()
        self.assertFalse(diverter.active)

        self.hit_switch_and_run("s_ball_switch1", 1)
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_target
        self.machine.playfield.add_ball()

        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter.enable.called
        self.assertEqual(0, diverter.diverting_ejects_count)

    def test_hold_activation_time(self):
        diverter = self.machine.diverters.d_test_hold_activation_time

        self.machine.coils.c_diverter.enable = MagicMock()
        self.machine.coils.c_diverter.disable = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_trough
        self.machine.playfield.add_ball()

        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)
        self.machine.coils.c_diverter.enable.assert_called_once_with()
        self.machine.coils.c_diverter.enable = MagicMock()
        assert not self.machine.coils.c_diverter.disable.called

        self.advance_time_and_run(4)
        self.machine.coils.c_diverter.disable.assert_called_once_with()
        assert not self.machine.coils.c_diverter.enable.called

        self.hit_and_release_switch("s_playfield")
        self.machine_run()
        self.assertFalse(diverter.active)

        self.hit_switch_and_run("s_ball_switch1", 1)
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_target
        self.machine.playfield.add_ball()

        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter.enable.called

    def test_hold_no_activation_time(self):
        diverter = self.machine.diverters.d_test_hold

        self.assertEqual("idle", self.machine.ball_devices.test_trough._state)
        self.assertEqual("idle", self.machine.ball_devices.test_target._state)

        self.machine.coils.c_diverter.enable = MagicMock()
        self.machine.coils.c_diverter.disable = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        # test active side
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_trough
        self.machine.playfield.add_ball()

        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)
        self.machine.coils.c_diverter.enable.assert_called_once_with()
        self.machine.coils.c_diverter.enable = MagicMock()
        assert not self.machine.coils.c_diverter.disable.called

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter.disable.called

        self.hit_and_release_switch("s_playfield")
        self.machine_run()
        self.assertFalse(diverter.active)
        self.machine.coils.c_diverter.disable.assert_called_once_with()

        self.hit_switch_and_run("s_ball_switch1", 1)
        # test inactive side
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_target
        self.machine.playfield.add_ball()

        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter.enable.called

        self.hit_switch_and_run("s_ball_switch1", 1)

    def test_missing_ball_at_source(self):
        diverter = self.machine.diverters.d_test
        trough1 = self.machine.ball_devices.test_trough
        target = self.machine.ball_devices.test_target

        self.machine.default_platform.actions[trough1].set_result("missing")
        trough1.eject(1, target)
        self.advance_time_and_run(1)
        self.assertEqual(1, diverter.diverting_ejects_count)

        self.advance_time_and_run(100)

        self.assertEqual(0, diverter.diverting_ejects_count)

    def test_eject_to_oposide_sides2(self):
        diverter = self.machine.diverters.d_test_hold
        trough1 = self.machine.ball_devices.test_trough
        trough2 = self.machine.ball_devices.test_trough2
        playfield = self.machine.playfield
        target = self.machine.ball_devices.test_target

        self.assertEqual(3, trough1.balls)
        self.assertEqual(3, trough2.balls)

        trough1.eject(1, playfield)
        trough2.eject(1, target)
        trough1.eject(1, playfield)
        trough2.eject(1, playfield)
        trough1.eject(1, target)
        trough2.eject(1, target)

        self.advance_time_and_run(100)

        self.assertEqual("idle", trough1._state)
        self.assertEqual("idle", trough2._state)

        self.assertEqual(0, diverter.diverting_ejects_count)

        self.assertEqual(3, playfield.balls)
        self.assertEqual(3, target.balls)
        self.assertEqual(0, trough1.balls)
        self.assertEqual(0, trough2.balls)

    def test_eject_to_oposide_sides(self):
        diverter = self.machine.diverters.d_test_hold
        trough1 = self.machine.ball_devices.test_trough
        trough2 = self.machine.ball_devices.test_trough2
        playfield = self.machine.playfield
        target = self.machine.ball_devices.test_target

        pulse1 = self.machine.coils.eject_coil1.pulse
        pulse3 = self.machine.coils.eject_coil3.pulse

        self.machine.coils.eject_coil1.pulse = MagicMock(wraps=pulse1)
        self.machine.coils.eject_coil3.pulse = MagicMock(wraps=pulse3)

        # this goes to the active side of the diverter
        trough1.eject(1, playfield)
        # this goes to the inactive side of the diverter
        trough2.eject(1, target)

        self.advance_time_and_run(5)

        self.assertEqual("ball_left", trough1._state)
        self.assertEqual("waiting_for_target_ready", trough2._state)

        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)

        # only trough1 ejects. trought2 waits because of diverter
        self.assertTrue(self.machine.coils.eject_coil1.pulse.called)
        assert not self.machine.coils.eject_coil3.pulse.called
        self.assertEqual(1, diverter.diverting_ejects_count)

        self.hit_and_release_switch("s_playfield")
        self.advance_time_and_run(3)
        # wait for cooldown
        self.assertFalse(self.machine.coils.eject_coil3.pulse.called)
        self.assertEqual(1, diverter.diverting_ejects_count)
        self.advance_time_and_run(3)
        self.assertTrue(self.machine.coils.eject_coil3.pulse.called)
        self.assertEqual(1, diverter.diverting_ejects_count)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.coils.eject_coil1.pulse = MagicMock(wraps=pulse1)
        self.machine.coils.eject_coil3.pulse = MagicMock(wraps=pulse3)

        self.machine.ball_devices.test_target.eject()
        self.advance_time_and_run(20)

        self.assertEqual("idle", trough1._state)
        self.assertEqual("idle", trough2._state)
        self.assertEqual(2, trough1.balls)
        self.assertEqual(1, trough2.balls)

        self.assertEqual("idle", target._state)
        self.assertEqual(0, diverter.diverting_ejects_count)

        self.machine.log.info("START")

        # same scenario but change order
        trough2.eject(1, target)
        trough1.eject(1, playfield)

        self.advance_time_and_run(0.05)

        self.assertEqual("waiting_for_target_ready", trough1._state)
        self.assertEqual("ball_left", trough2._state)

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.assertTrue(self.machine.coils.eject_coil3.pulse.called)
        assert not self.machine.coils.eject_coil1.pulse.called

        self.hit_and_release_switch("s_playfield")
        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        # wait for cooldown
        self.advance_time_and_run(3)

        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)

        self.assertTrue(self.machine.coils.eject_coil1.pulse.called)
        self.advance_time_and_run(20)

        self.assertEqual(0, diverter.diverting_ejects_count)

    def test_pulsed_activation_time(self):
        diverter = self.machine.diverters.d_test_pulse

        self.machine.coils.c_diverter.pulse = MagicMock()
        self.machine.coils.c_diverter_disable.pulse = MagicMock()

        self.post_event("machine_reset_phase_3")
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)
        self.assertTrue(self.machine.coils.c_diverter_disable.pulse.called)
        assert not self.machine.coils.c_diverter.pulse.called

        self.assertEqual("idle", self.machine.ball_devices.test_trough._state)
        self.assertEqual("idle", self.machine.ball_devices.test_target._state)

        self.machine.coils.c_diverter.pulse = MagicMock()
        self.machine.coils.c_diverter_disable.pulse = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_trough
        self.machine.playfield.add_ball()

        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)
        self.assertTrue(self.machine.coils.c_diverter.pulse.called)
        self.machine.coils.c_diverter.pulse = MagicMock()
        assert not self.machine.coils.c_diverter_disable.pulse.called

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter_disable.pulse.called

        self.hit_and_release_switch("s_playfield")
        self.machine_run()
        self.assertFalse(diverter.active)
        self.assertTrue(self.machine.coils.c_diverter_disable.pulse.called)

        self.hit_switch_and_run("s_ball_switch1", 1)
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_target
        self.machine.playfield.add_ball()

        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter.pulse.called
        self.assertEqual(0, diverter.diverting_ejects_count)

    def test_diverter_with_switch(self):
        diverter = self.machine.diverters.d_test

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        # it should not activate
        self.hit_and_release_switch("s_activate")
        self.advance_time_and_run(1)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        # nothing should happen
        self.hit_and_release_switch("s_deactivate")
        self.hit_and_release_switch("s_disable")
        self.advance_time_and_run(1)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        # enable diverter
        diverter.enable()
        self.assertTrue(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_activate")
        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)

        self.hit_and_release_switch("s_deactivate")
        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_activate")
        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)

        self.hit_and_release_switch("s_disable")
        self.advance_time_and_run(1)
        self.assertFalse(diverter.enabled)
        self.assertTrue(diverter.active)

        self.hit_and_release_switch("s_deactivate")
        self.advance_time_and_run(1)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

    def test_diverter_auto_disable(self):
        diverter = self.machine.diverters.d_test

        # enable diverter
        diverter.enable()
        self.assertTrue(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_activate")
        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)

        self.hit_and_release_switch("s_disable")
        self.advance_time_and_run(1)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

    def test_activation_switch_and_eject_confirm_switch(self):
        diverter = self.machine.diverters.d_test_hold_activation_time

        self.machine.coils.c_diverter.enable = MagicMock()
        self.machine.coils.c_diverter.disable = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_trough2
        self.machine.playfield.add_ball()

        self.advance_time_and_run(.01)
        self.assertTrue(diverter.enabled)
        self.assertFalse(diverter.active)

        # smart virtual automatically triggers the diverter
        self.advance_time_and_run(3)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)
        self.machine.coils.c_diverter.enable.assert_called_once_with()
        self.machine.coils.c_diverter.enable = MagicMock()
        assert not self.machine.coils.c_diverter.disable.called

        self.advance_time_and_run(4)
        self.machine.coils.c_diverter.disable.assert_called_once_with()
        assert not self.machine.coils.c_diverter.enable.called

        self.hit_and_release_switch("s_playfield")
        self.machine_run()
        self.assertFalse(diverter.active)

        self.hit_switch_and_run("s_ball_switch1", 1)
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_target
        self.machine.ball_devices.test_trough2.eject(1, self.machine.ball_devices.test_target)

        self.advance_time_and_run(.01)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        # smart virtual htis diverter switch for us
        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter.enable.called
        self.assertEqual(0, diverter.diverting_ejects_count)

    def test_diverter_dual_wound_coil(self):
        diverter = self.machine.diverters.d_test_dual_wound

        self.assertEqual("idle", self.machine.ball_devices.test_trough._state)
        self.assertEqual("idle", self.machine.ball_devices.test_target._state)

        self.machine.coils.c_hold.enable = MagicMock()
        self.machine.coils.c_hold.disable = MagicMock()
        self.machine.coils.c_power.pulse = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        # test active side
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_trough
        self.machine.playfield.add_ball()

        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)
        self.machine.coils.c_hold.enable.assert_called_once_with()
        self.machine.coils.c_hold.enable = MagicMock()
        self.assertTrue(self.machine.coils.c_power.pulse.called)
        self.machine.coils.c_power.pulse = MagicMock()
        assert not self.machine.coils.c_hold.disable.called

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_hold.disable.called

        self.hit_and_release_switch("s_playfield")
        self.machine_run()
        self.assertFalse(diverter.active)
        self.machine.coils.c_hold.disable.assert_called_once_with()

        self.hit_switch_and_run("s_ball_switch1", 1)
        # test inactive side
        self.machine.playfield.config['default_source_device'] = self.machine.ball_devices.test_target
        self.machine.playfield.add_ball()

        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.hit_and_release_switch("s_diverter")
        self.advance_time_and_run(0.5)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_hold.enable.called
        assert not self.machine.coils.c_power.pulse.called

        self.hit_switch_and_run("s_ball_switch1", 1)
