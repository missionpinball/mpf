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

# Documentation and more info at http://missionpinball.com/mpf

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

        self.start_button_pressed_time = 0.0
        self.start_hold_time = 0.0
        self.start_buttons_held = set()

        self.assets_waiting = 0

    def start(self, **kwargs):
        """ Automatically called when the Attract game mode becomes active.

        """
        super(Attract, self).start()

        if not self.machine.num_assets_to_load:
            self._do_start()
        else:
            self.machine.events.add_handler('timer_tick', self._loading_tick,
                                            10000)

    def stop(self):
        super(Attract, self).stop()
        self.machine.events.post('machineflow_attract_stop')
        self.machine.events.post('attract_stop')

    def _loading_tick(self):

        if self.machine.num_assets_to_load:

            if self.assets_waiting != self.machine.num_assets_to_load:

                self.log.info("Holding Attract start while assets load. "
                              "Remaining: %s", self.machine.num_assets_to_load)

                self.machine.events.post('assets_to_load',
                                         assets=self.machine.num_assets_to_load)

                self.assets_waiting = self.machine.num_assets_to_load

        else:
            self.log.info("Asset loading complete")
            self.machine.events.post('assets_loading_complete')
            self._do_start()

    def _do_start(self):

        self.machine.events.remove_handler(self._loading_tick)

        self.machine.events.post('machineflow_attract_start')
        self.machine.events.post('attract_start')

        # register switch handlers for the start button press so we can
        # capture long presses

        # add these to the registered_switch_handlers list so they'll be removed
        for switch in self.machine.switches.items_tagged('start'):
            self.registered_switch_handlers.append(
                self.machine.switch_controller.add_switch_handler(
                    switch.name, self.start_button_pressed, 1))
            self.registered_switch_handlers.append(
                self.machine.switch_controller.add_switch_handler(
                    switch.name, self.start_button_released, 0))

        if (hasattr(self.machine, 'balldevices') and
                self.machine.balldevices.items_tagged('home')):
            self.machine.ball_controller.gather_balls('home')

        self.machine.events.post('enable_volume_keys')

    def start_button_pressed(self):
        self.start_button_pressed_time = time.time()

    def start_button_released(self):
        """ Called when the a switch tagged with *start* is activated.

        Since this is the Attract mode, this method posts a boolean event
        called *request_to_start_game*. If that event comes back True, this
        method calls :meth:`result_of_start_request`.

        """
        self.start_hold_time = time.time() - self.start_button_pressed_time

        if hasattr(self.machine, 'flippers'):

            for flipper in self.machine.flippers:
                if self.machine.switch_controller.is_active(
                        flipper.config['activation_switch']):
                    self.start_buttons_held.add(flipper.config['activation_switch'])

        # todo test for active?
        # todo should this be a decorator?
        self.machine.events.post_boolean('request_to_start_game',
                                         callback=self.result_of_start_request)

    def result_of_start_request(self, ev_result=True):
        """Called after the *request_to_start_game* event is posted.

        If `result` is True, this method posts the event
        *machineflow_advance*. If False, nothing happens, as the game start
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
            self.machine.events.post('machineflow_advance',
                                     buttons=self.start_buttons_held,
                                     hold_time=self.start_hold_time)
            # machine flow will move on to the next mode when this mode ends

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
