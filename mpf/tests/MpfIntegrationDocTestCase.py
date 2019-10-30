from mpf.tests.MpfDocTestCase import MpfDocTestCase
from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase


class MpfIntegrationDocTestCase(MpfDocTestCase, MpfIntegrationTestCase, MpfSlideTestCase):

    def command_assert_slide_active(self, name):
        self.assertSlideActive(name)

    def command_assert_slide_not_active(self, name):
        self.assertSlideNotActive(name)

    def command_assert_text_in_slide(self, text, slide_name):
        self.assertTextInSlide(text, slide_name)

    def command_assert_text_not_in_slide(self, text, slide_name):
        self.assertTextNotInSlide(text, slide_name)

    def command_assert_slide_on_top(self, slide_name):
        self.assertSlideOnTop(slide_name)

    def command_assert_text_on_top_slide(self, slide_name):
        self.assertTextOnTopSlide(slide_name)

    def command_assert_text_not_on_top_slide(self, slide_name):
        self.assertTextNotOnTopSlide(slide_name)