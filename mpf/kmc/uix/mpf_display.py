from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import ScreenManager

class MpfDisplay(RelativeLayout):

    def __init__(self, **kwargs):

        super(MpfDisplay, self).__init__(**kwargs)

        self.screen_manager = ScreenManager()
        self.add_widget(self.screen_manager)

    def _sort_children(self):


