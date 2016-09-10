from mpf.integration.MpfIntegrationTest import MpfIntegrationTest
from mpf.integration.MpfSlideTestCase import MpfSlideTestCase
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestService(MpfIntegrationTest, MpfFakeGameTestCase, MpfSlideTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'integration/machine_files/service_mode/'

    def test_service_slides(self):
        # open door
        self.hit_switch_and_run("s_door_open", 1)
        self.assertModeRunning("attract")
        self.assertSlideOnTop("service_door_open")
        self.assertTextOnTopSlide("Coil Power Off")

        # enter
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertSlideOnTop("service_menu")
        self.assertTextOnTopSlide("Switch Test")

        # enter switch test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertSlideOnTop("service_switch_test")

        self.hit_and_release_switch("s_test")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("s_test")
        self.assertTextOnTopSlide("The test switch label")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertSlideOnTop("service_menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("Coil Test")

        # enter coil test
        self.hit_and_release_switch("s_service_enter")
        self.advance_time_and_run()
        self.assertSlideOnTop("service_coil_test")
        self.assertTextOnTopSlide("c_test")
        self.assertTextOnTopSlide("First coil")
        self.assertTextOnTopSlide("Coil Power Off")

        # close door
        self.release_switch_and_run("s_door_open", 1)
        self.assertTextNotOnTopSlide("Coil Power Off")

        # exit
        self.hit_and_release_switch("s_service_esc")
        self.advance_time_and_run()
        self.assertSlideOnTop("service_menu")

        self.hit_and_release_switch("s_service_up")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("Settings")
