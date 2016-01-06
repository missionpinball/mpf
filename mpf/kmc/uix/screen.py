from kivy.properties import ObjectProperty
from kivy.properties import NumericProperty
from kivy.properties import DictProperty
from kivy.uix.screenmanager import Screen as KivyScreen

class Screen(KivyScreen):

    mode = ObjectProperty(None, allownone=True)
    ''':class:`Mode` object, which is the mode that created this screen.'''

    priority = NumericProperty(0)
    '''Priority of this screen.'''

    config = DictProperty()
    '''Dict which holds the settings for this screen, including all the widgets
    that are on it and their properties.'''

    def __init__(self, name, manager, config, **kwargs):
        super(Screen, self).__init__(**kwargs)

        self.name = name
        self.manager = manager
        self.config = config
