"""Contains the Keyboard class which allows a computer keyboard to be used to
activate switches for MPF Python games.

"""
# keyboard.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import pyglet

# todo do not set toggle keys if real hw is being used.


class Keyboard(object):
    """Base class which allows a computer keyboard to be used to similate
    switch activity in a pinball machine. This is good for testing purposes
    when you aren't sitting at the actual machine.

    The Keyboard class gets its settings from the Machine Configuration Files
    in the [keymap] section.

    This module uses a pyglet window to capture the key events.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger('Keyboard')
        self.keyboard_events = []
        self.key_map = {}
        self.toggle_keys = {}
        self.inverted_keys = []
        self.start_active = []
        self._setup_window()

        # register for events
        self.machine.events.add_handler('timer_tick', self.get_keyboard_events)
        self.machine.events.add_handler('machine_init_complete',
                                        self.set_initial_states, 100)

        # Setup the key mappings

        self.log.debug("Setting up the keyboard mappings")
        for k, v in self.machine.config['key_map'].iteritems():
            k = str(k)  # k is the value of the key entry in the config
            switch_name = v.get('switch', None)
            # set whether a key is the push on / push off type
            toggle_key = v.get('toggle', None)
            # set whether a toggle key starts
            start_active = v.get('start_active', None)
            # todo convert to True from true or TRUE
            invert = v.get('invert', None)
            event = v.get('event', None)  # todo
            # todo add args processing?
            # will hold our key entry converted to pyglet key format
            pyglet_key = ""
            # the built-up command we'll use to convert pyglet_key to our
            # key_code entry
            key_code = ""

            # Process the key map entry
            # convert to everything to uppercase for backwards compatibility
            k = k.upper()

            # there's more than one list item, meaning we have a modifier key
            if len(k) > 1:
                k = k.split('-')  # convert our key entry into a list
                # reverse the list order so the base key is always in pos 0
                k.reverse()
                # stores the added together value of the modifier keys
                mod_value = 0
                # loop through the modifier keys and add their values together
                for i in range((len(k)-1)):
                    # convert entry to pyglet key code
                    mod_value += int(eval("pyglet.window.key.MOD_" + k[i+1]))
                # add the dash back in to separate mod value from the key code
                key_code = str(mod_value) + "-"

            # convert key entry from the config to a pyglet key code.
            # Lots of ifs here to catch all the options
            # if it's a single alpha character
            if len(str(k[0])) == 1 and str(k[0]).isalpha():
                pyglet_key = str(k[0])
            # if it's a single digit
            elif len(str(k[0])) == 1 and str(k[0]).isdigit():
                pyglet_key = "_" + str(k[0])
            # Other single character stuff for backwards compatibility
            elif str(k[0]) == "/":
                pyglet_key = "SLASH"
            elif str(k[0]) == ".":
                pyglet_key = "PERIOD"
            elif str(k[0]) == ",":
                pyglet_key = "COMMA"
            elif str(k[0]) == "-":
                pyglet_key = "MINUS"
            elif str(k[0]) == "=":
                pyglet_key = "EQUAL"
            elif str(k[0]) == ";":
                pyglet_key = "SEMICOLON"

            # now the catch all to try anything else that's specified.
            else:
                pyglet_key = str(k[0])
            try:
                # we use "try" so it doesn't crash if there's an invalid key
                # name
                key_code = key_code + str(eval("pyglet.window.key." +
                                               str(pyglet_key)))
            except:
                self.log.warning("%s is not a valid pyglet key code. "
                                 "Skipping this entry", pyglet_key)

            if switch_name:  # We're processing a key entry for a switch

                # if a hardware switch is type 'NC', we need to invert the
                # keyboard switch. Note that "invert: True" is not needed in
                # the keymap file. In fact if you have it then you will
                # invert the invert. :)
                if self.machine.switches[switch_name].type == 'NC':
                    invert = not invert

                if invert:
                    self.inverted_keys.append(switch_name)
                # Finally it's time to add the new pyglet code / switch number
                # pair to the key map
                self.add_key_map(str(key_code), switch_name, toggle_key,
                                 start_active, invert)

                if start_active:
                    self.start_active.append(switch_name)

            elif event:
                # todo add event processing
                pass

    def add_key_map(self, key, switch_name, toggle_key=False,
                    start_active=False, invert=False):
        """Maps the given *key* to *switch_name*, where *key* is one of the
        key constants in :mod:`pygame.locals`."""
        # todo add event processing
        if isinstance(key, basestring):
            # deletes any random zeros that come through as modifiers
            if key[0:2] == '0-':
                key = key[2:]
        self.key_map[key] = switch_name

        if toggle_key:
            key = str(key)
            if start_active and not self.machine.physical_hw:
                # if the initial switch stated should be active, set it
                self.toggle_keys[key] = 1
            else:
                self.toggle_keys[key] = 0

            if invert:
                self.toggle_keys[key] = self.toggle_keys[key] ^ 1

    def set_initial_states(self):
        """Sets the initial states of all the switches by activating switches
        configured to start active.

        """
        # don't set the initial state if we have physical hw
        if not self.machine.physical_hw:
            for switch_name in self.start_active:
                self.log.debug("Setting initial state of switch '%s' to "
                               "active", switch_name)

                self.machine.switch_controller.process_switch(state=1,
                                                              name=switch_name,
                                                              logical=True)

    def get_keyboard_events(self):
        """Gets the key events from the pyglet window."""
        self.window.dispatch_events()

    def _setup_window(self):
        self.window = pyglet.window.Window()

        @self.window.event
        def on_close():
            self.machine.done = True

        @self.window.event
        # capture key presses and add them to the event queue
        def on_key_press(symbol, modifiers):
            if (symbol == pyglet.window.key.C and
                    modifiers & pyglet.window.key.MOD_CTRL) or \
                    (symbol == pyglet.window.key.ESCAPE):
                #self.append_exit_event()
                self.machine.done = True

            else:
                key_press = str(symbol)
                # if a modifier key was pressed along with the regular key,
                # combine them in the way they're in the key_map

                if modifiers & 8:  # '8' is the plyglet mod value for caps lock
                    modifiers -= 8  # so we just remove it.

                if modifiers & 16:  # Same for '16' which is for num lock
                    modifiers -= 16

                if modifiers:
                    key_press = str(modifiers) + "-" + key_press

                # check our built-up key_press string against the existing
                # key_map dictionary
                if key_press in self.toggle_keys:  # is this is a toggle key?
                    if self.toggle_keys.get(key_press) == 1:
                        # Switch is currently closed, so open it
                        self.machine.switch_controller.process_switch(state=0,
                            name=self.key_map[key_press])
                        self.toggle_keys[key_press] = 0
                    else:  # Switch is currently open, so close it
                        self.toggle_keys[key_press] = 1
                        self.machine.switch_controller.process_switch(state=1,
                            name=self.key_map[key_press])

                elif key_press in self.key_map:
                    # for non-toggle keys, still want to make sure the key is
                    # valid

                    if self.key_map[key_press] in self.inverted_keys:
                        self.machine.switch_controller.process_switch(state=0,
                            name=self.key_map[key_press])
                    else:
                        self.machine.switch_controller.process_switch(state=1,
                            name=self.key_map[key_press])

        @self.window.event
        def on_key_release(symbol, modifiers):
            # see the above on_key_press() method for comments on this method
            key_press = str(symbol)
            if modifiers:
                key_press = str(modifiers) + "-" + key_press

            # if our key is valid and not in the toggle_keys dictionary,
            # process the key up event
            if key_press in self.key_map and key_press not in self.toggle_keys:
                if self.key_map[key_press] in self.inverted_keys:
                    self.machine.switch_controller.process_switch(state=1,
                        name=self.key_map[key_press])
                else:
                    self.machine.switch_controller.process_switch(state=0,
                        name=self.key_map[key_press])

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
