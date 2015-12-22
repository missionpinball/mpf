from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import ScreenManager, Screen


class MyDisplay(RelativeLayout):

    def __init__(self, **kwargs):
        self.size_hint = (None, None)
        super(MyDisplay, self).__init__(**kwargs)
        self.screen_manager = ScreenManager()
        self.add_widget(self.screen_manager)

    def on_size(self, width, height):
        pass

class MyLabel(Label):

    def __init__(self, **kwargs):

        self.size_hint = (None, None)

        super(MyLabel, self).__init__(**kwargs)

        self.texture_update()
        self.size = self.texture_size


class MyApp(App):

    def build(self):
        self.display = MyDisplay(width=800, height=600)
        self.display.bind(size=self.size_change)

        return self.display

    def finish_building(self):
        new_screen = Screen(name='test')
        new_screen.add_widget(MyLabel(text='HELLO'))
        self.display.screen_manager.add_widget(new_screen)
        self.display.screen_manager.current = 'test'

    def size_change(self):
        print(self.display.size)
        self.finish_building()

MyApp().run()