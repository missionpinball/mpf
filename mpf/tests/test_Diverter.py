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

    def test_hold_activation_time(self):
        diverter = self.machine.diverters.d_test_hold_activation_time

        self.machine.coils.c_diverter.enable = MagicMock()
        self.machine.coils.c_diverter.disable = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.ball_devices.test_trough.tags.append("ball_add_live")
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
        self.machine.ball_devices.test_trough.tags.remove("ball_add_live")
        self.machine.ball_devices.test_target.tags.append("ball_add_live")
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
        self.machine.ball_devices.test_trough.tags.append("ball_add_live")
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
        self.machine.ball_devices.test_trough.tags.remove("ball_add_live")
        self.machine.ball_devices.test_target.tags.append("ball_add_live")
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
        self.assertEqual("ejecting", trough2._state)

        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)

        # only trough1 ejects. trought2 waits because of diverter
        self.machine.coils.eject_coil1.pulse.assert_called_once_with()
        assert not self.machine.coils.eject_coil3.pulse.called
        self.assertEqual(1, diverter.diverting_ejects_count)

        self.hit_and_release_switch("s_playfield")
        self.advance_time_and_run(3)
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)
        self.machine.coils.eject_coil3.pulse.assert_called_once_with()
        self.assertEqual(0, diverter.diverting_ejects_count)

        self.machine.coils.eject_coil1.pulse = MagicMock(wraps=pulse1)
        self.machine.coils.eject_coil3.pulse = MagicMock(wraps=pulse3)

        self.machine.ball_devices.test_target.eject()
        self.advance_time_and_run(20)

        self.assertEqual("idle", trough1._state)
        self.assertEqual("idle", trough2._state)
        self.assertEqual("idle", target._state)
        self.assertEqual(0, diverter.diverting_ejects_count)

        self.machine.log.info("START")

        # same scenario but change order
        trough2.eject(1, target)
        trough1.eject(1, playfield)

        self.advance_time_and_run(0.05)

        self.assertEqual("ejecting", trough1._state)
        self.assertEqual("ball_left", trough2._state)

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.coils.eject_coil3.pulse.assert_called_once_with()
        assert not self.machine.coils.eject_coil1.pulse.called

        self.hit_and_release_switch("s_playfield")
        self.advance_time_and_run(3)

        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)

        self.machine.coils.eject_coil1.pulse.assert_called_once_with()

    def test_pulsed_activation_time(self):
        diverter = self.machine.diverters.d_test_pulse

        self.machine.coils.c_diverter.pulse = MagicMock()
        self.machine.coils.c_diverter_disable.pulse = MagicMock()

        self.post_event("machine_reset_phase_3")
        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)
        self.machine.coils.c_diverter_disable.pulse.assert_called_once_with()
        assert not self.machine.coils.c_diverter.pulse.called

        self.assertEqual("idle", self.machine.ball_devices.test_trough._state)
        self.assertEqual("idle", self.machine.ball_devices.test_target._state)

        self.machine.coils.c_diverter.pulse = MagicMock()
        self.machine.coils.c_diverter_disable.pulse = MagicMock()

        self.assertFalse(diverter.enabled)
        self.assertFalse(diverter.active)

        self.machine.ball_devices.test_trough.tags.append("ball_add_live")
        self.machine.playfield.add_ball()

        self.advance_time_and_run(1)
        self.assertTrue(diverter.enabled)
        self.assertTrue(diverter.active)
        self.machine.coils.c_diverter.pulse.assert_called_once_with()
        self.machine.coils.c_diverter.pulse = MagicMock()
        assert not self.machine.coils.c_diverter_disable.pulse.called

        self.advance_time_and_run(4)
        assert not self.machine.coils.c_diverter_disable.pulse.called

        self.hit_and_release_switch("s_playfield")
        self.machine_run()
        self.assertFalse(diverter.active)
        self.machine.coils.c_diverter_disable.pulse.assert_called_once_with()

        self.hit_switch_and_run("s_ball_switch1", 1)
        self.machine.ball_devices.test_trough.tags.remove("ball_add_live")
        self.machine.ball_devices.test_target.tags.append("ball_add_live")
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

        self.machine.ball_devices.test_trough2.tags.append("ball_add_live")
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
        self.machine.ball_devices.test_trough2.tags.remove("ball_add_live")
        self.machine.ball_devices.test_target.tags.append("ball_add_live")
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
        self.machine.ball_devices.test_trough.tags.append("ball_add_live")
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
        self.machine.coils.c_power.pulse.assert_called_once_with()
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
        self.machine.ball_devices.test_trough.tags.remove("ball_add_live")
        self.machine.ball_devices.test_target.tags.append("ball_add_live")
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
