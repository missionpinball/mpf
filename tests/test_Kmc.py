
from .KmcTestCase import KmcTestCase


class TestKmc(KmcTestCase):

    def test_kmc_start(self):
        from kivy.core.window import Window
        print(Window.size)
