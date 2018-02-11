"""Motor device."""
from mpf.core.events import event_handler
from mpf.core.system_wide_device import SystemWideDevice


class Motor(SystemWideDevice):

    """A motor which can be controlled using drivers."""

    config_section = 'motors'
    collection = 'motors'
    class_label = 'motor'

    def __init__(self, machine, name):
        """Initialise motor."""
        self._target_position = None
        super().__init__(machine, name)

    def _initialize(self):
        super()._initialize()
        self._target_position = self.config['reset_position']
        if self.config['reset_position'] not in self.config['position_switches']:
            raise AssertionError("Invalid reset position")

        # add handlers
        for event, position in self.config['go_to_position'].items():
            if position not in self.config['position_switches']:
                raise AssertionError("Invalid position {} in go_to_position".format(position))
            self.machine.events.add_handler(event, self.go_to_position, position=position)

        if self.config['include_in_ball_search']:
            self.machine.events.add_handler("ball_search_started",
                                            self._ball_search_start)
            self.machine.events.add_handler("ball_search_stopped",
                                            self._ball_search_stop)

    @event_handler(1)
    def reset(self, **kwargs):
        """Go to reset position."""
        del kwargs
        self.go_to_position(self.config['reset_position'])

    @event_handler(10)
    def go_to_position(self, position, **kwargs):
        """Move motor to a specific position."""
        del kwargs
        self.log.info("Moving motor to position %s", position)
        self._target_position = position
        self._move_to_position(position)

    def _move_to_position(self, position):
        switch = self.config['position_switches'][position]
        # check if we are already in this position
        if self.machine.switch_controller.is_active(switch.name):
            # already in position
            self._reached_position(position)
        else:
            # not in position. start motor
            self.config['motor_coil'].enable()

            # remove previous handlers
            for position_switch in self.config['position_switches'].values():
                self.machine.switch_controller.remove_switch_handler(position_switch.name, self._reached_position)

            # add new handler for new position
            self.machine.switch_controller.add_switch_handler(
                switch.name, self._reached_position, callback_kwargs={"position": position})

    def _reached_position(self, position, **kwargs):
        """Handle that motor reached a certain position."""
        del kwargs
        self.debug_log("Motor is in position %s", position)

        self.machine.events.post("motor_{}_reached_{}".format(self.name, position))
        '''event: motor_(name)_reached_(position)

        desc: A motor device called (name) reached position (position)
        (device)
        '''

        # disable motor
        self.config['motor_coil'].disable()

    def _remove_handlers(self):
        # remove previous handlers
        for position_switch in self.config['position_switches'].values():
            self.machine.switch_controller.remove_switch_handler(position_switch.name, self._reached_position)

    def _ball_search_start(self, **kwargs):
        del kwargs
        # simply enable motor. will move to old position afterwards.
        self.config['motor_coil'].enable()

    def _ball_search_stop(self, **kwargs):
        del kwargs
        # move to last position
        self._move_to_position(self._target_position)
