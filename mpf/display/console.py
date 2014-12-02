""" MPF display plugin which redirects display output to the console window.
NOTE: This module is not complete and does not work yet.."""
# console.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging


# todo formatters
# default formatting


class ConsoleDisplay(object):

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("ConsoleDisplay")
        self.log.debug("Loading the ConsoleDisplay")

        self.color_map = {
                        'black': 0,
                        'red': 1,
                        'green': 2,
                        'yellow': 3,
                        'blue': 4,
                        'magenta': 5,
                        'cyan': 6,
                        'white': 7,
                        }

        self.machine.events.add_handler('timer_tick', self.tick)

        self.current_text = None

    def tick(self):
        if (self.machine.display.frame and
                self.current_text != self.machine.display.frame[0]['text']):
            self.current_text = self.machine.display.frame[0]['text']
            self.text(self.current_text)

    def text(self, text, priority=0, time=-1, **kwargs):
        text = ''.join(('\x1b[', ';'.join(['41', '36', '1']), 'm', text, '\x1b[0m'))
        print text

        # list is bg (+40), fg (+30), bold (1)

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