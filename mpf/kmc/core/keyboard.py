
from kivy.uix.widget import Widget
from kivy.core.window import Window


class MyKeyboardListener(Widget):


    def __init__(self, mc, **kwargs):
        super(MyKeyboardListener, self).__init__(**kwargs)

        self.mc = mc

        self.keyboard_events = list()
        self.key_map = dict()
        self.toggle_keys = set()
        self.inverted_keys = list()
        self.active_keys = dict()

        self._keyboard = Window.request_keyboard(
            self._keyboard_closed, self, 'text')

        if self._keyboard.widget:
            # If it exists, this widget is a VKeyboard object which you can use
            # to change the keyboard layout.
            pass
        self._keyboard.bind(on_key_down=self._on_keyboard_down,
                            on_key_up=self._on_keyboard_up)
        
        
        for k, v in self.mc.machine_config['keyboard'].items():
            k = str(k)  # k is the value of the key entry in the config
            switch_name = v.get('switch', None)
            # set whether a key is the push on / push off type
            toggle_key = v.get('toggle', None)
            invert = v.get('invert', None)
            event = v.get('event', None)
            mc_event = v.get('mc_event', None)
            params = v.get('params', None)
            # todo add args processing?


            # Process the key map entry
            k = k.replace('+', '-').lower().split('-')

            # There are lots of different modifier key values, and they really
            # vary depending on the platform. So rather than stripping out ones
            # we don't need, we're going to only look for the ones we can use:
            # SHIFT, ALT, CTRL, and META

            key = k[-1]
            mods = k[:-1]

            # What happens when it's pressed?

            if switch_name:  # We're processing a key entry for a switch

                if invert:
                    self.inverted_keys.append(switch_name)

                self.add_key_map(key, mods, switch_name, toggle_key, invert)

            elif event:  # we're processing an entry for an event
                event_dict = {'event': event, 'params': params}
                self.add_key_map(key, mods, event_dict=event_dict)

            elif mc_event:  # we're processing an entry for an mc_event
                event_dict = {'mc_event': mc_event, 'params': params}
                self.add_key_map(key, mods, event_dict=event_dict)

    def get_key_string(self, key, mods):
        return '{}-{}'.format(key, '-'.join(mods))

    def add_key_map(self, key, mods, switch_name=None, toggle_key=False,
                    invert=False, event_dict=None):
        """Adds an entry to the key_map which is used to see what to do when
        key events are received.

        Args:
            key: The character or name of the key
            mods: List of strings for modifier keys for this entry
            switch_name: String name of the switch this key combination is tied
                to.
            toggle_key: Boolean as to whether this key should be a toggle key.
                (i.e. push on / push off).
            invert: Boolean as to whether this key combination should be
                inverted. (Key down = switch inactive, key up = switch active.)
                Default is False.
            event_dict: Dictionary of events with parameters that will be posted
                when this key combination is pressed. Default is None.

        """
        key_string = self.get_key_string(key, mods)

        if switch_name:
            self.key_map[key_string] = switch_name
        elif event_dict:
            self.key_map[key_string] = event_dict

        if toggle_key:
            self.toggle_keys.add(key_string)

    def _on_keyboard_up(self, keyboard, keycode):
        key = keycode[1]
        self.process_key_release(key)
        return True

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]

        if key in self.active_keys:
            return True
        else:
            return self.process_key_down(key, modifiers)

    def process_key_down(self, key, mods):

        key_string = self.get_key_string(key, mods)

        if key_string not in self.key_map:
            return False

        if key_string in self.toggle_keys:  # is this is a toggle key?
            self.active_keys[key] = None
            self.send_switch(state=-1, name=self.key_map[key_string])

        else:
            # do we have an event or a switch?
            if type(self.key_map[key_string]) == str:  # switch

                if self.key_map[key_string] in self.inverted_keys:
                    self.send_switch(state=0, name=self.key_map[key_string])
                    self.active_keys[key] = ''.join(('-',
                                                     self.key_map[key_string]))

                else:
                    self.send_switch(state=1, name=self.key_map[key_string])
                    self.active_keys[key] = self.key_map[key_string]

            elif type(self.key_map[key_string]) == dict:  # event
                event_dict = self.key_map[key_string]
                event_params = event_dict['params'] or {}

                if 'event' in event_dict:

                    print("sending event", event_dict['event'])

                    self.mc.send(bcp_command='trigger',
                                 name=str(event_dict['event']),
                                 **event_params)

                elif 'mc_event' in event_dict:

                    print("sending mc_event", event_dict['mc_event'])

                    self.mc.events.post(event_dict['mc_event'],
                                                 **event_params)

        return True

    def process_key_release(self, key):
        action = self.active_keys.pop(key, None)

        if action:
            if action.startswith('-'):
                self.send_switch(state=1, name=action[1:])
            else:
                self.send_switch(state=0, name=action)

    def send_switch(self, name, state):
        print("sending switch", name, state)
        self.mc.bcp_processor.send('switch', name=name, state=state)

    def _keyboard_closed(self):
        print('My keyboard have been closed!')
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None