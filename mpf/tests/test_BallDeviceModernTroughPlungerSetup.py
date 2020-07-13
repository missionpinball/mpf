from mpf.tests.MpfTestCase import MpfTestCase


class TestBallDeviceModernTroughPlungerSetup(MpfTestCase):

    def get_platform(self):
        return "smart_virtual"

    def get_config_file(self):
        return 'test_modern_trough_plunger_setup.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_ball_in_plunger_during_eject(self):
        # add some initial balls
        self.hit_switch_and_run("s_trough_switch1", 0)
        self.hit_switch_and_run("s_trough_switch2", 0)
        self.hit_switch_and_run("s_trough_switch3", 1)
        self.assertNumBallsKnown(3)

        self.machine.playfield.add_ball()
        self.hit_switch_and_run("s_ball_switch_plunger_lane", 0)
        self.advance_time_and_run(100)

        self.assertEqual("idle", self.machine.ball_devices["bd_trough"].state)
        self.assertEqual("idle", self.machine.ball_devices["bd_plunger"].state)
        self.assertBallsOnPlayfield(2)
        self.assertNumBallsKnown(4)


class TestBallDeviceModernTroughPlungerSetupRaces(MpfTestCase):

    def get_platform(self):
        return "virtual"

    def get_config_file(self):
        return 'test_modern_trough_plunger_setup.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def test_ball_in_plunger_during_eject(self):
        # add some initial balls
        self.mock_event("balldevice_bd_trough_ejecting_ball")
        self.mock_event("balldevice_bd_plunger_ejecting_ball")
        self.mock_event("balldevice_bd_trough_ball_eject_success")
        self.mock_event("balldevice_bd_plunger_ball_eject_success")
        self.hit_switch_and_run("s_trough_switch1", 0)
        self.hit_switch_and_run("s_trough_switch2", 0)
        self.hit_switch_and_run("s_trough_switch3", 1)
        self.advance_time_and_run(10)
        self.assertNumBallsKnown(3)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.3)
        self.assertEventCalled("balldevice_bd_trough_ejecting_ball")
        self.mock_event("balldevice_bd_trough_ejecting_ball")
        self.assertEventNotCalled("balldevice_bd_plunger_ejecting_ball")
        self.release_switch_and_run("s_trough_switch3", 1)

        self.hit_switch_and_run("s_ball_switch_plunger_lane", 0)
        self.advance_time_and_run(10)
        self.assertEventNotCalled("balldevice_bd_trough_ejecting_ball")
        self.assertEventCalled("balldevice_bd_plunger_ejecting_ball")
        self.mock_event("balldevice_bd_plunger_ejecting_ball")

        self.release_switch_and_run("s_ball_switch_plunger_lane", 0)
        self.advance_time_and_run(3)

        self.assertEventNotCalled("balldevice_bd_trough_ejecting_ball")
        self.assertEventNotCalled("balldevice_bd_plunger_ejecting_ball")

        self.hit_and_release_switch("s_playfield")
        self.advance_time_and_run(20)

        self.assertEventNotCalled("balldevice_bd_trough_ejecting_ball")
        self.assertEventNotCalled("balldevice_bd_plunger_ejecting_ball")
        self.assertEventCalled("balldevice_bd_trough_ball_eject_success", 1)
        self.assertEventCalled("balldevice_bd_plunger_ball_eject_success", 1)

        self.assertEqual("idle", self.machine.ball_devices["bd_trough"].state)
        self.assertEqual("idle", self.machine.ball_devices["bd_plunger"].state)
        self.assertBallsOnPlayfield(1)
        self.assertNumBallsKnown(3)

    def test_eject_failure_with_jam(self):
        """Trough jams but pluger confirms eject."""
        # add some initial balls
        self.mock_event("balldevice_bd_trough_ejecting_ball")
        self.mock_event("balldevice_bd_plunger_ejecting_ball")
        self.mock_event("balldevice_bd_trough_ball_eject_success")
        self.mock_event("balldevice_bd_trough_ball_eject_failed")
        self.mock_event("balldevice_bd_plunger_ball_eject_success")
        self.hit_switch_and_run("s_trough_switch1", 0)
        self.hit_switch_and_run("s_trough_switch2", 0)
        self.hit_switch_and_run("s_trough_switch3", 1)
        self.advance_time_and_run(10)
        self.assertNumBallsKnown(3)

        self.machine.playfield.add_ball()
        self.advance_time_and_run(.1)
        self.assertEventCalled("balldevice_bd_trough_ejecting_ball")
        self.mock_event("balldevice_bd_trough_ejecting_ball")
        self.assertEventNotCalled("balldevice_bd_plunger_ejecting_ball")
        self.hit_switch_and_run("s_trough_jam", 0)
        self.release_switch_and_run("s_trough_switch3", .25)
        self.hit_switch_and_run("s_trough_switch3", .25)
        self.release_switch_and_run("s_trough_switch1", 0)

        # eject timeout not passed yet
        self.advance_time_and_run(1.51)
        self.assertEventNotCalled("balldevice_bd_trough_ball_eject_failed")
        self.assertEventNotCalled("balldevice_bd_trough_ball_eject_success")

        # unexpected playfield activation happens (i.e. broken switch)
        self.hit_and_release_switch("s_playfield")

        # event timeout passes
        self.advance_time_and_run(1)
        self.assertEventCalled("balldevice_bd_trough_ball_eject_failed")
        self.assertEventNotCalled("balldevice_bd_trough_ball_eject_success")

        self.hit_and_release_switch("s_playfield")

        self.assertEqual("ejecting", self.machine.ball_devices["bd_trough"].state)
        self.assertEqual("waiting_for_ball", self.machine.ball_devices["bd_plunger"].state)

        self.assertEventCalled("balldevice_bd_trough_ejecting_ball", 1)
        self.release_switch_and_run("s_trough_jam", 0)

        self.advance_time_and_run(20)

        self.assertEqual("idle", self.machine.ball_devices["bd_trough"].state)
        self.assertEqual("idle", self.machine.ball_devices["bd_plunger"].state)

        self.assertBallsOnPlayfield(1)
        self.assertNumBallsKnown(3)
