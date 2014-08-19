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

    def __init__(self, machine):
        super(Attract, self).__init__(machine)
        self.log = logging.getLogger("Attract Mode")
        self.delay = DelayManager()
        self.holding_coil = None

    def start(self):
        """ Automatically called when the Attract game mode becomes active.

        """
        super(Attract, self).start()
        # register event handlers
        self.registered_event_handlers.append(
            self.machine.events.add_handler('sw_start',
            self.start_button_pressed))

        self.machine.ball_controller.gather_balls('home')

        self.machine.events.add_handler('coil_test', self.coil_test)
        self.machine.events.add_handler('advance_reel_test', self.advance_reel)
        self.machine.events.add_handler('hold_coil', self.hold_coil)

    ###########################################################################
    ### The following section holds temporary methods we're using for       ###
    ### testing our Big Shot EM machine.                                    ###
    ###########################################################################

    def coil_test(self, coil_name, pulse_change=0):
        if pulse_change:
            self.machine.coils[coil_name].pulse_ms += pulse_change
            self.log.debug("+-----------------------------------------------+")
            self.log.debug("|                                               |")
            self.log.debug("|   Coil: %s   New pulse time: %s           |",
                           self.machine.coils[coil_name].name,
                           self.machine.coils[coil_name].pulse_ms)
            self.log.debug("|                                               |")
            self.log.debug("+-----------------------------------------------+")
        else:
            self.log.debug("+-----------------------------------------------+")
            self.log.debug("|                                               |")
            self.log.debug("|   Coil: %s   PULSING: %s                |",
                           self.machine.coils[coil_name].name,
                           self.machine.coils[coil_name].pulse_ms)
            self.log.debug("|                                               |")
            self.log.debug("+-----------------------------------------------+")
            self.machine.coils[coil_name].pulse()

    def advance_reel(self, reel_name, direction=1):
        self.machine.score_reels[reel_name].advance(int(direction))

    def hold_coil(self, coil_name, hold_time):
        self.delay.add('kill_the_coil', hold_time, self.hold_coil_kill)
        self.holding_coil = coil_name
        self.machine.coils[coil_name].enable()

    def hold_coil_kill(self):
        self.machine.coils[self.holding_coil].disable()

    def test(self, param=None):
        print "test"
        print "param", param

    ## End of temp section
    ###########################################################################

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

    def tick(self):
        """Called once per machine tick.

        Currently this method does nothing. Eventually it will drive the DMD
        and do other Attract-type things.

        """
        while self.active:
            # do something here
            yield

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
