"""MPF plugin which automatically plays back switch events from the config file."""

import logging
from mpf.core.delays import DelayManager
from mpf.core.utility_functions import Util


class SwitchPlayer(object):

    """Plays back switch sequences from a config file, used for testing."""

    def __init__(self, machine):
        """Initialise switch player."""
        self.log = logging.getLogger('switch_player')

        if 'switch_player' not in machine.config:
            machine.log.debug('"switch_player:" section not found in '
                              'machine configuration, so the Switch Player'
                              'plugin will not be used.')
            return

        self.machine = machine
        self.delay = DelayManager(self.machine.delayRegistry)
        self.current_step = 0

        self.config = self.machine.config['switch_player']
        self.machine.config_validator.validate_config("switch_player", self.config)

        self.machine.events.add_handler(self.config['start_event'],
                                        self._start_event_callback)

        self.step_list = self.config['steps']

    def __repr__(self):
        """Return string representation."""
        return '<SwitchPlayer>'

    def _start_event_callback(self, **kwargs):
        del kwargs
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
        if self.current_step < len(self.step_list) - 1:
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
