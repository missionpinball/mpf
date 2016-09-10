from unittest.mock import MagicMock

from mpf.core.settings_controller import SettingEntry
from mpf.integration.MpfIntegrationTest import MpfIntegrationTest
from mpf.integration.MpfSlideTestCase import MpfSlideTestCase
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestService(MpfIntegrationTest, MpfSlideTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'integration/machine_files/widgets_and_slides/'

    def test_widget_on_slide_of_another_mode(self):
        self.post_event("start_mode1")
        self.advance_time_and_run()
        self.post_event("show_widget_mode1_on_slide_mode2")
        self.advance_time_and_run()

        self.assertSlideNotActive("slide_mode2")

        self.post_event("start_mode2")
        self.advance_time_and_run()
        self.post_event("show_slide_mode2")
        self.advance_time_and_run()

        self.assertSlideOnTop("slide_mode2")
        self.assertTextInSlide("Widget Mode 1", "slide_mode2")
