"""MPF pluging which allows a computer keyboard to be used to activate switches
for MPF Python games.

"""
# keyboard.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging

# todo do not set toggle keys if real hw is being used.

global import_success

try:
    import pygame
    import pygame.locals
    import_success = True
except:
    import_success = False


def preload_check(machine):

    if import_success:
        return True
    else:
        return False


class Keyboard(object):
    """Base class which allows a computer keyboard to be used to similate
    switch activity in a pinball machine. This is good for testing purposes
    when you aren't sitting at the actual machine.

    The Keyboard class gets its settings from the Machine Configuration Files
    in the [keymap] section.

    This module uses a Pygame window to capture the key events.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """

    def __init__(self, machine):
        self.log = logging.getLogger('Keyboard')
        self.machine = machine

        self.keyboard_events = []
        self.key_map = {}
        self.toggle_keys = {}
        self.inverted_keys = []
        self.start_active = []

        self.machine.request_pygame()
        self.window = self.machine.get_window()

        # register for events
        self.machine.events.add_handler('machine_init_phase3',
                                        self.set_initial_states, 100)

        # register event handlers to get key actions from the Pygame window
        self.machine.window_manager.register_handler(pygame.locals.KEYDOWN,
                                                     self.process_key_press)
        self.machine.window_manager.register_handler(pygame.locals.KEYUP,
                                                     self.process_key_release)

        # Set up the key mappings
        self.log.debug("Setting up the keyboard mappings")

        if 'Keyboard' not in self.machine.config:
            return
            # Even if there are no keys configured, we still want to use this
            # module if it's in the plugins list since it allows the player to
            # use the Esc key to quit MPF.

        for k, v in self.machine.config['Keyboard'].iteritems():
            k = str(k)  # k is the value of the key entry in the config
            switch_name = v.get('switch', None)
            # set whether a key is the push on / push off type
            toggle_key = v.get('toggle', None)
            # set whether a toggle key starts
            start_active = v.get('start_active', None)
            # todo convert to True from true or TRUE
            invert = v.get('invert', None)
            event = v.get('event', None)
            params = v.get('params', None)
            # todo add args processing?
            # will hold our key entry converted to pygame key format
            pygame_key = ""
            # the built-up command we'll use to convert pygame_key to our
            # key_code entry
            key_code = ""

            # Process the key map entry
            # convert to everything to uppercase
            k = k.upper()

            # Check to see if there's a dash. That means we have a modifier key
            if '-' in k:
                # convert the key entry into a list
                k = k.split('-')

                # reverse the list order so the base key is always in pos 0
                k.reverse()

                # stores the added together value of the modifier keys
                mod_value = 0
                # loop through the modifier keys and add their values together
                for i in range((len(k)-1)):
                    # convert entry to pygame key code
                    try:
                        int(eval("pygame.locals.KMOD_" + k[i+1]))
                    except:
                        self.log.warning("Found an invalid keyboard modifier: "
                                         "%s. Ignoring...", k[i+1])
                # add the dash back in to separate mod value from the key code
                key_code = str(mod_value) + "-"

            # convert key entry from the config to a pygame key code.
            # Lots of ifs here to catch all the options

            # if it's a single alpha character
            if len(str(k[0])) == 1 and str(k[0]).isalpha():
                pygame_key = str(k[0]).lower()

            # if it's a single digit
            elif len(str(k[0])) == 1 and str(k[0]).isdigit():
                pygame_key = str(k[0])

            # Other single character stuff for backwards compatibility
            elif str(k[0]) == "/":
                pygame_key = "SLASH"
            elif str(k[0]) == ".":
                pygame_key = "PERIOD"
            elif str(k[0]) == ",":
                pygame_key = "COMMA"
            elif str(k[0]) == "-":
                pygame_key = "MINUS"
            elif str(k[0]) == "=":
                pygame_key = "EQUALS"
            elif str(k[0]) == ";":
                pygame_key = "SEMICOLON"
            else:  # Catch all to try anything else that's specified
                pygame_key = str(k[0])

            try:
                # using "try" so it doesn't crash if there's an invalid key
                key_code = key_code + str(eval("pygame.locals.K_" +
                                               str(pygame_key)))
            except:
                self.log.warning("%s is not a valid Pygame key code. "
                                 "Skipping this entry", pygame_key)

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

            elif event:  # we're processing an entry for an event
                event_dict = {'event': event, 'params': params}
                self.add_key_map(str(key_code), event_dict=event_dict)

    def add_key_map(self, key, switch_name=None, toggle_key=False,
                    start_active=False, invert=False, event_dict=None):
        """Maps the given *key* to *switch_name*, where *key* is one of the
        key constants in :mod:`pygame.locals`."""
        # todo add event processing
        if isinstance(key, basestring):
            # deletes any random zeros that come through as modifiers
            if key[0:2] == '0-':
                key = key[2:]
        if switch_name:
            self.key_map[key] = switch_name
        elif event_dict:
            self.key_map[key] = event_dict

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

                # Use set_state() instead of process_switch() so this mimics
                # the physical hw process.
                self.machine.switch_controller.process_switch(name=switch_name,
                                                              state=1,
                                                              logical=True)

    # capture key presses and add them to the event queue
    def process_key_press(self, symbol, modifiers):
        if (symbol == pygame.locals.K_c and
                modifiers & pygame.locals.KMOD_CTRL) or \
                (symbol == pygame.locals.K_ESCAPE):
            #self.append_exit_event()
            self.machine.done = True

        else:
            key_press = str(symbol)
            # if a modifier key was pressed along with the regular key,
            # combine them in the way they're in the key_map

            # First remove modifiers we want to ignore

            if modifiers & pygame.locals.K_SCROLLOCK:
                modifiers -= pygame.locals.K_SCROLLOCK

            if modifiers & pygame.locals.K_NUMLOCK:
                modifiers -= pygame.locals.K_NUMLOCK

            if modifiers & pygame.locals.K_CAPSLOCK:
                modifiers -= pygame.locals.K_CAPSLOCK

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
                    # do we have an event or a switch?
                    if type(self.key_map[key_press]) == str:
                        # we have a switch
                        self.machine.switch_controller.process_switch(
                            state=1, name=self.key_map[key_press])
                    elif type(self.key_map[key_press]) == dict:
                        # we have an event
                        event_dict = self.key_map[key_press]
                        self.machine.events.post(str(event_dict['event']),
                                                 **event_dict['params'])

    def process_key_release(self, symbol, modifiers):
        # see the above process_key_press() method for comments on this method
        key_press = str(symbol)

        if modifiers & 8:  # '8' is the plyglet mod value for caps lock
            modifiers -= 8  # so we just remove it.

        if modifiers & 16:  # Same for '16' which is for num lock
            modifiers -= 16

        if modifiers:
            key_press = str(modifiers) + "-" + key_press

        # if our key is valid and not in the toggle_keys dictionary,
        # process the key up event

        if key_press in self.key_map and key_press not in self.toggle_keys:
            if self.key_map[key_press] in self.inverted_keys:
                self.machine.switch_controller.process_switch(state=1,
                    name=self.key_map[key_press])
            elif type(self.key_map[key_press]) == str:
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
