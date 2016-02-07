"""MPF plugin which automatically plays back switch events from the config
file."""

import logging

from mpf.core.config import Config
from mpf.core.delays import DelayManager


class SwitchPlayer(object):

    def __init__(self, machine):
        self.log = logging.getLogger('switch_player')

        if 'switch_player' not in machine.config:
            machine.log.debug('"switch_player:" section not found in '
                                   'machine configuration, so the Switch Player'
                                   'plugin will not be used.')
            return

        self.machine = machine
        self.delay = DelayManager(self.machine.delayRegistry)
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

    def __repr__(self):
        return '<SwitchPlayer>'

    def _start_event_callback(self):

        if ('time' in self.step_list[self.current_step] and
                self.step_list[self.current_step]['time'] > 0):

            self.delay.add(name='switch_player_next_step',
                           ms=Util.string_to_ms(self.step_list[self.current_step]['time']),
                           callback=self._do_step)

    def _do_step(self):

            this_step = self.step_list[self.current_step]

            self.log.debug("Switch: %s, Action: %s", this_step['switch'],
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
                               ms=Util.string_to_ms(self.step_list[self.current_step]['time']),
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
