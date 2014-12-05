"""MPF plugin which automatically puts game info on the display (score, balls,
players, etc.)."""
# info_display.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging


def preload_check(machine):

    if 'InfoDisplay' in machine.config:
        return True
    else:
        return False


class InfoDisplay(object):
    """Parent class for InfoDisplay objects which are things you configure via
    the machine config files that let you display text messages based on game
    events. You can use this to show game status, players, scores, etc. Any
    setting that is available via the text method of the display controller is
    available here, including positioning, fonts, size, delays, etc.
    """

    def __init__(self, machine):
        self.log = logging.getLogger('InfoDisplay')
        self.machine = machine
        self.config = self.machine.config['InfoDisplay']

        for event, settings in self.config.iteritems():
            if 'text' in settings:
                if 'priority' not in settings:
                    settings['priority'] = 0
                if 'time' not in settings:
                    settings['time'] = 0

                self.setup_text_handler(event, **settings)

    def setup_text_handler(self, event, **kwargs):
        """Sets up a text handler that will automatically call a text()
        diplay event when an MPF event is posted.

        Args:
            event: A string of the event name
            kwargs: One or more keyword values that you want to pass to the
            text() display event. (See that documentation for details of what
            these options are. These include things like "text", "font", "time,"
            "size", position information, priority, etc.

            Note that for text values, you can use a % sign followed by a string
            that will be pulled as a kwarg from the event. For example, the
            event 'player_add_success' includes a keyword "num" which is the
            player number that was added, so you can specify a text string
            'PLAYER %num ADDED' and it will be rendered as 'PLAYER 2 ADDED', for
            example.

            Also note that if you're specifying these text strings via the YAML
            configuration file, you can't start a string with a percent sign.
            In that case you can wrap the string in quotes in your YAML file.

            For example:
                text: %score <-- will give an error
                text: "%score" <-- OK

        """
        self.machine.events.add_handler(event, self._display_text,
                                        **kwargs)

    def _display_text(self, text, priority=0, time=0, **kwargs):
        # Internal method which actually displays the text
        for kw in kwargs:
            if '%' + kw in text:
                text = text.replace('%' + kw, str(kwargs[kw]))

        self.machine.display.text(text, priority, time, **kwargs)

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