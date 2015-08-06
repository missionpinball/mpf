"""MPF plugin which automatically plays back switch events from the config
file."""
# switch_player.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging

from mpf.system.config import Config
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing


class SwitchPlayer(object):

    def __init__(self, machine):
        self.log = logging.getLogger('switch_player')

        if 'switch_player' not in machine.config:
            machine.log.debug('"switch_player:" section not found in '
                                   'machine configuration, so the Switch Player'
                                   'plugin will not be used.')
            return

        self.machine = machine
        self.delay = DelayManager()
        self.current_step = 0

        config_spec = '''
                        start_event: string|machine_reset_phase_3
                        start_delay: secs|0
                        '''

        self.config = Config.process_config(config_spec,
                                            self.machine.config['switch_player'])

        self.machine.events.add_handler(self.config['start_event'],
                                        self._start_event_callback)

        self.step_list = self.config['steps']
        self.start_delay = self.config['start_delay']

    def _start_event_callback(self):

        if ('time' in self.step_list[self.current_step] and
                self.step_list[self.current_step]['time'] > 0):

            self.delay.add(name='switch_player_next_step',
                           ms=Timing.string_to_ms(self.step_list[self.current_step]['time']),
                           callback=self._do_step)

    def _do_step(self):

            this_step = self.step_list[self.current_step]

            self.log.info("Switch: %s, Action: %s", this_step['switch'],
                          this_step['action'])

            # send this step's switches
            if this_step['action'] == 'activate':
                self.machine.switch_controller.process_switch(
                    this_step['switch'],
                    state=1,
                    logical=True)
            elif this_step['action'] == 'deactivate':
                self.machine.switch_controller.process_switch(
                    this_step['switch'],
                    state=0,
                    logical=True)
            elif this_step['action'] == 'hit':
                self._hit(this_step['switch'])

            # inc counter
            if self.current_step < len(self.step_list)-1:
                self.current_step += 1

                # schedule next step
                self.delay.add(name='switch_player_next_step',
                               ms=Timing.string_to_ms(self.step_list[self.current_step]['time']),
                               callback=self._do_step)

    def _hit(self, switch):
        self.machine.switch_controller.process_switch(
                    switch,
                    state=1,
                    logical=True)
        self.machine.switch_controller.process_switch(
                    switch,
                    state=0,
                    logical=True)


plugin_class = SwitchPlayer

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
