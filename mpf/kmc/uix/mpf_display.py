from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import ScreenManager

class MpfDisplay(RelativeLayout):

    def __init__(self, **kwargs):

        self.size_hint = (None, None)

        super(MpfDisplay, self).__init__(**kwargs)


        # Window.add_widget(self)

        # self.add_widget(Label(text="hello3"))

        self.screen_manager = ScreenManager()
        self.add_widget(self.screen_manager)

        # screen = Screen()
        # screen.add_widget(Label(text="hello3"))

        print(kwargs)
        print('%%%%%%%%%%%%%%%%', self.size)