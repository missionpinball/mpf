from mpf.tests.MpfTestCase import MpfTestCase


class MpfSlideTestCase(MpfTestCase):

    def assertSlideOnTop(self, slide_name, target="default"):
        self.assertEqual(slide_name, self.mc.targets[target].current_slide.name)

    def assertTextOnTopSlide(self, text, target="default"):
        self.assertTextInSlide(text, self.mc.targets[target].current_slide.name)

    def assertTextNotOnTopSlide(self, text, target="default"):
        self.assertTextNotInSlide(text, self.mc.targets[target].current_slide.name)

    def assertSlideActive(self, slide_name):
        self.assertIn(slide_name, self.mc.active_slides, "Slide {} is not active.".format(slide_name))

    def assertSlideNotActive(self, slide_name):
        self.assertNotIn(slide_name, self.mc.active_slides, "Slide {} is active but should not.".format(slide_name))

    def assertTextInSlide(self, text, slide_name):
        self.assertSlideActive(slide_name)
        self.assertIn(text, [x.text for x in self.mc.active_slides[slide_name].children[0].children],
                      "Text {} not found in slide {}.".format(text, slide_name))

    def assertTextNotInSlide(self, text, slide_name):
        self.assertSlideActive(slide_name)
        self.assertNotIn(text, [x.text for x in self.mc.active_slides[slide_name].children[0].children],
                         "Text {} found in slide {} but should not be there.".format(text, slide_name))