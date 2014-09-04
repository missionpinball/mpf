"""Contains the Attract class which is the attract mode in a pinball machine.

.. Note::
   Still need to add the code to watch for combinations of  button presses,
   like a long-press, pressing start while holding a flipper button, holding a
   flipper button to start tournament mode, etc.

"""
# attract.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from mpf.system.machine_mode import MachineMode
from mpf.system.tasks import DelayManager
import time


class Attract(MachineMode):
    """ Base class for the active mode for a machine when a game is not in
    progress. It's main job is to watch for the start button to be pressed, to
    post the requests to start games, and to move the machine flow to the next
    mode if the request to start game comes back as approved.

    Parameters
    ----------

    machine : :class:`MachineController`
        A reference to the instance of the MachineController object.

    """

    def __init__(self, machine, name):
        super(Attract, self).__init__(machine, name)
        self.log = logging.getLogger("Attract Mode")
        self.delay = DelayManager()

    def start(self):
        """ Automatically called when the Attract game mode becomes active.

        """
        super(Attract, self).start()
        # register event handlers
        self.registered_event_handlers.append(
            self.machine.events.add_handler('sw_start',
                                            self.start_button_pressed))

        self.machine.ball_controller.gather_balls('home')

    def start_button_pressed(self):
        """ Called when the a switch tagged with *start* is activated.

        Since this is the Attract mode, this method posts a boolean event
        called *request_to_start_game*. If that event comes back True, this
        method calls :meth:`result_of_start_request`.

        """
        # todo test for active?
        # todo should this be a decorator?
        self.log.debug("Received start button press")
        self.machine.events.post('request_to_start_game', ev_type='boolean',
                                 callback=self.result_of_start_request)

    def result_of_start_request(self, ev_result=True):
        """Called after the *request_to_start_game* event is posted.

        If `result` is True, this method posts the event
        *machine_flow_advance*. If False, nothing happens, as the game start
        request was denied by some handler.

        Parameters
        ----------

        result : bool
            Result of the boolean event *request_to_start_game. If any
            registered event handler did not want the game to start, this will
            be False. Otherwise it's True.

        """
        if ev_result is False:
            self.log.debug("Game start was denied")
        else:  # else because we want to start on True *or* None
            self.log.debug("Let's start a game!!")
            self.machine.events.post('machine_flow_advance')
            # machine flow will move on to the next mode when this mode ends

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
