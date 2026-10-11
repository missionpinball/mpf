from unittest.mock import MagicMock

from mpf.tests.MpfTestCase import MpfTestCase


class TestBallDeviceMultipleEject(MpfTestCase):

    """One eject pulse releases more balls than requested (e.g. a lock post
    that drops and lets every queued ball roll out)."""

    def get_config_file(self):
        return 'test_multiple_eject.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def _ball_reaches_vuk_and_is_kicked_to_playfield(self):
        self.hit_switch_and_run("s_vuk", 1)
        # kicked out; a playfield eject confirms once the ball stays out
        self.release_switch_and_run("s_vuk", 3)

    def test_one_pulse_releasing_every_queued_ball(self):
        lock = self.machine.ball_devices["test_lock"]
        vuk = self.machine.ball_devices["test_vuk"]
        playfield = self.machine.playfield
        self.machine.coils["c_lock_post"].pulse = MagicMock()
        self.machine.coils["c_vuk"].pulse = MagicMock()
        self.mock_event("balldevice_ball_missing")

        for switch in ("s_lock_1", "s_lock_2", "s_lock_3"):
            self.hit_switch_and_run(switch, 1)
        self.assertEqual(3, lock.balls)

        self.post_event("release_all", .1)
        self.assertEqual(1, self.machine.coils["c_lock_post"].pulse.call_count)

        # the post drops: every queued ball leaves on that single pulse
        for switch in ("s_lock_1", "s_lock_2", "s_lock_3"):
            self.release_switch_and_run(switch, .05)
        self.advance_time_and_run(1)

        for _ in range(3):
            self._ball_reaches_vuk_and_is_kicked_to_playfield()
        self.advance_time_and_run(10)

        self.assertEventNotCalled("balldevice_ball_missing")
        self.assertEqual(1, self.machine.coils["c_lock_post"].pulse.call_count)
        self.assertEqual(0, lock.balls)
        self.assertEqual(0, lock.available_balls)
        self.assertEqual("idle", lock._state)
        self.assertEqual(0, vuk.balls)
        self.assertEqual(0, vuk.available_balls)
        self.assertEqual("idle", vuk._state)
        self.assertEqual(playfield.balls, playfield.available_balls)

    def test_surplus_ball_only_fulfils_an_eject_to_the_same_target(self):
        lock = self.machine.ball_devices["test_lock"]
        vuk = self.machine.ball_devices["test_vuk"]
        playfield = self.machine.playfield
        self.machine.coils["c_lock_post"].pulse = MagicMock()
        self.machine.coils["c_vuk"].pulse = MagicMock()
        lock_eject_targets = []
        self.machine.events.add_handler(
            "balldevice_test_lock_ejecting_ball",
            lambda target, **kwargs: lock_eject_targets.append(target))

        for switch in ("s_lock_1", "s_lock_2"):
            self.hit_switch_and_run(switch, 1)
        self.machine.ball_holds["hold_lock"].disable()
        lock.eject(1, target=vuk)
        lock.eject(1, target=playfield)
        self.advance_time_and_run(.1)

        # the post drops for the VUK eject: both balls roll to the VUK
        for switch in ("s_lock_1", "s_lock_2"):
            self.release_switch_and_run(switch, .05)
        self.advance_time_and_run(1)
        for _ in range(2):
            self._ball_reaches_vuk_and_is_kicked_to_playfield()
        self.advance_time_and_run(10)

        # the surplus ball went to the VUK, not to the playfield
        self.assertEqual([vuk], lock_eject_targets)

        # the playfield eject is still owed: the next ball serves it
        self.hit_switch_and_run("s_lock_1", 1)
        self.assertEqual([vuk, playfield], lock_eject_targets[:2])
        self.assertEqual(2, self.machine.coils["c_lock_post"].pulse.call_count)
