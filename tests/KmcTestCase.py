
import unittest

from kivy.config import Config
from mpf.system.utility_functions import Util

Config.set('kivy', 'log_enable', '0')
Config.set('kivy', 'log_level', 'warning')

from mpf.kmc.core.kmc import KmcApp


class KmcTestCase(unittest.TestCase):

    def get_options(self):

        return dict(machine_path=self.get_machine_path(),
                    kmcconfigfile='mpf/kmc/kmcconfig.yaml',
                    configfile=Util.string_to_list(self.get_config_file()))

    def get_machine_path(self):
        return '../tests/machine_files/kmc'

    def get_config_file(self):
        return 'test_kmc.yaml'

    def setUp(self):

        KmcApp(self.get_options()).run()
        return




        # use default kivy configuration (don't load user file.)
        from os import environ
        environ['KIVY_USE_DEFAULTCONFIG'] = '1'

        # force window size + remove all inputs
        from kivy.config import Config
        Config.set('graphics', 'width', '320')
        Config.set('graphics', 'height', '240')
        for items in Config.items('input'):
            Config.remove_option('input', items[0])

        # bind ourself for the later screenshot
        from kivy.core.window import Window
        Window.bind(on_flip=self.on_window_flip)

        # ensure our window is correcly created
        Window.create_window()
        Window.canvas.clear()

    def on_window_flip(self):
        pass

    def tearDown(self):
        pass