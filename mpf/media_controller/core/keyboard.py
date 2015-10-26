"""MC keyboard processor"""
# keyboard.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging

# todo do not set toggle keys if real hw is being used.

global import_success

try:
    import pygame
    import pygame.locals
    import_success = True
except ImportError:
    import_success = False


def preload_check(mc):

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

    Args:
        mc: The main media controller object.

    """

    def __init__(self, mc):
        self.log = logging.getLogger('keyboard')
        self.mc = mc

        self.keyboard_events = list()
        self.key_map = dict()
        self.toggle_keys = set()
        self.inverted_keys = list()

        self.mc.request_pygame()
        self.window = self.mc.get_window()

        # register event handlers to get key actions from the Pygame window
        self.mc.register_pygame_handler(pygame.locals.KEYDOWN,
                                             self.process_key_press)
        self.mc.register_pygame_handler(pygame.locals.KEYUP,
                                             self.process_key_release)

        # Set up the key mappings
        self.log.debug("Setting up the keyboard mappings")

        if 'keyboard' not in self.mc.config:
            return
            # Even if there are no keys configured, we still want to use this
            # module if it's in the plugins list since it allows the player to
            # use the Esc key to quit MPF.

        for k, v in self.mc.config['keyboard'].iteritems():
            k = str(k)  # k is the value of the key entry in the config
            switch_name = v.get('switch', None)
            # set whether a key is the push on / push off type
            toggle_key = v.get('toggle', None)
            invert = v.get('invert', None)
            event = v.get('event', None)
            mc_event = v.get('mc_event', None)
            params = v.get('params', None)
            # todo add args processing?
            # will hold our key entry converted to pygame key format
            pygame_key = ""
            # the built-up command we'll use to convert pygame_key to our
            # key_code entry
            key_code = ""

            # Process the key map entry
            k = k.upper()  # convert to everything to uppercase
            k = k.replace('+', '-').split('-')

            # There are lots of different modifier key values, and they really
            # vary depending on the platform. So rather than stripping out ones
            # we don't need, we're going to only look for the ones we can use:
            # SHIFT, ALT, CTRL, and META

            mod_value = 0 # stores the added together value of the mod keys

            # loop through the modifier keys and add their values together
            for i in k[:-1]:
                if i.upper() == 'SHIFT':
                    mod_value += pygame.locals.KMOD_SHIFT

                elif i.upper() == 'ALT':
                    mod_value += pygame.locals.KMOD_ALT

                elif i.upper() == 'CTRL':
                    mod_value += pygame.locals.KMOD_CTRL

                elif i.upper() == 'META':
                    mod_value += pygame.locals.KMOD_META

                else:
                    self.log.warning("Found an invalid keyboard modifier: "
                                     "%s. Ignoring...", i)

            if mod_value:
                key_code = str(mod_value) + "-"

            # Convert key entry from the config to a pygame key code.

            # If it's a single alpha character
            if str(k[-1]).isalpha():
                pygame_key = str(k[-1]).lower()

            # If it's a single digit
            elif (k[-1]).isdigit():
                pygame_key = str(k[-1])

            # Other single character stuff
            elif str(k[-1]) == "/":
                pygame_key = "SLASH"
            elif str(k[-1]) == ".":
                pygame_key = "PERIOD"
            elif str(k[-1]) == ",":
                pygame_key = "COMMA"
            elif str(k[-1]) == "-":
                pygame_key = "MINUS"
            elif str(k[-1]) == "=":
                pygame_key = "EQUALS"
            elif str(k[-1]) == ";":
                pygame_key = "SEMICOLON"
            else:  # Catch all to try anything else that's specified
                pygame_key = str(k[-1])

            try:
                if len(pygame_key) == 1:
                    key_code += str(eval("pygame.locals.K_" +
                                               str(pygame_key).lower()))
                else:
                    key_code += str(eval("pygame.locals.K_" +
                                               str(pygame_key).upper()))
            except AttributeError:
                self.log.warning("'%s' is not a valid Pygame key code. "
                                 "Skipping...", pygame_key)

            # Now that we have the key code, what happens when it's pressed?

            if switch_name:  # We're processing a key entry for a switch

                if invert:
                    self.inverted_keys.append(switch_name)

                # Add the new Pygame code / switch number pair to the key map
                self.add_key_map(str(key_code), switch_name, toggle_key,
                                 invert)

            elif event:  # we're processing an entry for an event
                event_dict = {'event': event, 'params': params}
                self.add_key_map(str(key_code), event_dict=event_dict)

            elif mc_event:  # we're processing an entry for an mc_event
                event_dict = {'mc_event': mc_event, 'params': params}
                self.add_key_map(str(key_code), event_dict=event_dict)

    def add_key_map(self, key, switch_name=None, toggle_key=False,
                    invert=False, event_dict=None):
        """Adds an entry to the key_map which is used to see what to do when
        key events are received.

        Args:
            key: The built-up string of the key combination which optionally
                includes modifier keys.
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
<<<<<<< Updated upstream
            key = str(key)
            self.toggle_keys[key] = 0

            if invert:
                self.toggle_keys[key] ^= 1
=======
            self.toggle_keys.add(str(key))
>>>>>>> Stashed changes

    def process_key_press(self, symbol, modifiers):
        """Processes a key press (key down) event by setting the switch and/or
        posting the event to MPF.

        Args:
            symbol: The Pygame symbol of the key that was just pressed.
            modifiers: The Pygame modifier value for any modifier keys that were
                active along with this key event.
        """
        if (symbol == pygame.locals.K_c and
                modifiers & pygame.locals.KMOD_CTRL) or \
                (symbol == pygame.locals.K_ESCAPE):
            self.mc.shutdown()

        else:
            key_press = self.get_key_press_string(symbol, modifiers)

            # check our built-up key_press string against the existing
            # key_map dictionary
            if key_press in self.toggle_keys:  # is this is a toggle key?
                self.send_switch(state=-1, name=self.key_map[key_press])

            elif key_press in self.key_map:
                # for non-toggle keys, still want to make sure the key is
                # valid

                if self.key_map[key_press] in self.inverted_keys:
                    self.send_switch(state=0, name=self.key_map[key_press])
                else:
                    # do we have an event or a switch?
                    if type(self.key_map[key_press]) == str:
                        # we have a switch
                        self.send_switch(state=1, name=self.key_map[key_press])
                    elif type(self.key_map[key_press]) == dict:
                        # we have an event
                        event_dict = self.key_map[key_press]
                        event_params = event_dict['params'] or {}
<<<<<<< Updated upstream
                        self.mc.send(bcp_command='trigger',
                                     name=str(event_dict['event']),
                                     **event_params)
=======

                        if 'event' in event_dict:
                            self.mc.send(bcp_command='trigger',
                                         name=str(event_dict['event']),
                                         **event_params)

                        elif 'mc_event' in event_dict:
                            self.mc.events.post(event_dict['mc_event'],
                                                     **event_params)
>>>>>>> Stashed changes

    def process_key_release(self, symbol, modifiers):
        """Processes a key release (key up) event by setting the switch and/or
        posting the event to MPF.

        Args:
            symbol: The Pygame symbol of the key that was just released.
            modifiers: The Pygame modifier value for any modifier keys that were
                active along with this key event.

        """
        key_press = self.get_key_press_string(symbol, modifiers)

        # if our key is valid and not in the toggle_keys set, process the key
        # up event

        if key_press in self.key_map and key_press not in self.toggle_keys:
            if self.key_map[key_press] in self.inverted_keys:
                self.send_switch(state=1, name=self.key_map[key_press])
            elif type(self.key_map[key_press]) == str:
                self.send_switch(state=0, name=self.key_map[key_press])

    def get_key_press_string(self, symbol, modifiers):
        """Converts a Pygame key symbol with modifiers into the string format
        that MPF uses in its internal key map.

        Args:
            symbol: The Pygame symbol of the key.
            modifiers: The Pygame modifier value for any modifier keys that were
                active along with this key event.

        Returns: A string in the proper format MPF uses.
        """

        key_press = str(symbol)

        filtered_mod_keys = 0

        if modifiers & pygame.locals.KMOD_SHIFT:
            filtered_mod_keys += pygame.locals.KMOD_SHIFT

        if modifiers & pygame.locals.KMOD_CTRL:
            filtered_mod_keys += pygame.locals.KMOD_CTRL

        if modifiers & pygame.locals.KMOD_ALT:
            filtered_mod_keys += pygame.locals.KMOD_ALT

        if modifiers & pygame.locals.KMOD_META:
            filtered_mod_keys += pygame.locals.KMOD_META

        if filtered_mod_keys:
            key_press = str(filtered_mod_keys) + "-" + key_press

        return key_press

    def send_switch(self, name, state):
        self.mc.send('switch', name=name, state=state)


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

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
