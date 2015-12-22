from kivy.uix.screenmanager import Screen as KivyScreen

class Screen(KivyScreen):

    def __init__(self, name, config, **kwargs):
        super(Screen, self).__init__(name)

        assert self.name == name

