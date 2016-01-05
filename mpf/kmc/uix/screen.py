from kivy.uix.screenmanager import Screen as KivyScreen

class Screen(object):

    creation_id = 0

    @classmethod
    def get_creation_id(cls):
        Screen.creation_id += 1
        return Screen.creation_id

    def __init__(self, name, config, **kwargs):

        self.priority
        self.display


        self.id = Screen.get_creation_id()



        super(Screen, self).__init__(name)

        assert self.name == name

        # read in the config

        # set the parent screen manager

        # set the priority

        # set the mode

    def _create_kivy_screen(self):
        pass

    def add_widget(self):
        pass

    def remove_widget(self):
        pass
