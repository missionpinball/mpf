from unittest.mock import MagicMock

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestMagnet(MpfFakeGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/magnet/'

    def test_grab_and_release_and_fling(self):
        self.mock_event("magnet_magnet1_grabbing_ball")
        self.mock_event("magnet_magnet1_grabbed_ball")
        self.assertEqual("disabled", self.machine.coils.magnet_coil1.hw_driver.state)
        # hit switch
        self.hit_and_release_switch("grab_switch1")
        self.advance_time_and_run(.1)
        # magnet not enabled -> nothing happens
        self.assertEqual("disabled", self.machine.coils.magnet_coil1.hw_driver.state)
        # enable magnet and try again
        self.post_event("magnet1_enable")
        self.hit_and_release_switch("grab_switch1")
        self.advance_time_and_run(.1)

        # magnet enables
        self.assertEventCalled("magnet_magnet1_grabbing_ball")
        self.assertEventNotCalled("magnet_magnet1_grabbed_ball")
        self.assertEqual("enabled", self.machine.coils.magnet_coil1.hw_driver.state)

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
        self.assertEqual("disabled", self.machine.coils.magnet_coil1.hw_driver.state)
        self.assertEventCalled("magnet_magnet1_releasing_ball")
        self.assertEventNotCalled("magnet_magnet1_released_ball")

        # ball passes switch
        self.hit_and_release_switch("grab_switch1")

        # release done after .5s
        self.advance_time_and_run(.5)
        self.assertEventCalled("magnet_magnet1_releasing_ball")
        self.assertEventCalled("magnet_magnet1_released_ball")
        self.assertEqual("disabled", self.machine.coils.magnet_coil1.hw_driver.state)

        # grab again
        self.mock_event("magnet_magnet1_grabbing_ball")
        self.mock_event("magnet_magnet1_grabbed_ball")
        self.hit_and_release_switch("grab_switch1")
        self.advance_time_and_run(.1)

        # magnet enables
        self.assertEventCalled("magnet_magnet1_grabbing_ball")
        self.assertEventNotCalled("magnet_magnet1_grabbed_ball")
        self.assertEqual("enabled", self.machine.coils.magnet_coil1.hw_driver.state)

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
        self.assertEqual("disabled", self.machine.coils.magnet_coil1.hw_driver.state)
        self.assertEventCalled("magnet_magnet1_flinging_ball")
        self.assertEventNotCalled("magnet_magnet1_flinged_ball")

        # coil reenables
        self.advance_time_and_run(.25)
        self.assertEqual("enabled", self.machine.coils.magnet_coil1.hw_driver.state)
        self.assertEventCalled("magnet_magnet1_flinging_ball")
        self.assertEventNotCalled("magnet_magnet1_flinged_ball")

        # and disables again
        self.advance_time_and_run(.1)
        self.assertEqual("disabled", self.machine.coils.magnet_coil1.hw_driver.state)
        self.assertEventCalled("magnet_magnet1_flinging_ball")
        self.assertEventCalled("magnet_magnet1_flinged_ball")
