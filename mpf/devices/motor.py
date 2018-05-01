"""Motor device."""
import asyncio

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
        self._last_position = None
        self.type = None
        super().__init__(machine, name)

    @asyncio.coroutine
    def _initialize(self):
        yield from super()._initialize()
        super()._initialize()
        self._target_position = self.config['reset_position']
        if self.config['reset_position'] not in self.config['position_switches']:
            self.raise_config_error("Reset position {} not in positions {}".format(
                self.config['reset_position'], self.config['position_switches']), 1)

        if not self.config['motor_left_output'] and not self.config['motor_right_output']:
            self.raise_config_error("Need either motor_left_output or motor_right_output", 2)

        if self.config['motor_left_output'] == self.config['motor_right_output']:
            self.raise_config_error("motor_left_output and motor_right_output need to be different", 3)

        if self.config['motor_left_output'] and self.config['motor_right_output']:
            self.type = "two_directions"
            # add handlers to stop the motor when it reaches the end to prevent damage
            self.machine.switch_controller.add_switch_handler(
                next(iter(self.config['position_switches'].values())).name, self._end_reached)  # noqa
            self.machine.switch_controller.add_switch_handler(
                next(reversed(list(self.config['position_switches'].values()))).name, self._end_reached)    # noqa
        else:
            self.type = "one_direction"

        for position, switch in self.config['position_switches'].items():
            self.machine.switch_controller.add_switch_handler(switch.name, self._update_position,
                                                              callback_kwargs={"position": position})

        # add handlers
        for event, position in self.config['go_to_position'].items():
            if position not in self.config['position_switches']:
                self.raise_config_error("Invalid position {} in go_to_position".format(position), 4)
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
            if self.type == "two_directions":
                if self._last_position is None or list(self.config['position_switches']).index(self._last_position) > \
                        list(self.config['position_switches']).index(position):
                    self.config['motor_left_output'].enable()
                    self.config['motor_right_output'].disable()
                else:
                    self.config['motor_left_output'].disable()
                    self.config['motor_right_output'].enable()
            else:
                # not in position. start motor
                if self.config['motor_left_output']:
                    self.config['motor_left_output'].enable()
                else:
                    self.config['motor_right_output'].enable()

    def _end_reached(self, **kwargs):
        """Stop all motors since we reached one of the end switches."""
        del kwargs
        self.info_log("Motor hit end switch. Stopping motor.")
        self._stop_motor()

    def _update_position(self, position, **kwargs):
        """Handle that motor reached a certain position."""
        del kwargs
        self._last_position = position

        if position == self._target_position:
            self._reached_position(position)
        else:
            self.debug_log("Motor is at position %s", position)

    def _reached_position(self, position):
        """Handle that motor handled its target position."""
        self.info_log("Motor reached position %s. Stopping motor.", position)
        self.machine.events.post("motor_{}_reached_{}".format(self.name, position))
        '''event: motor_(name)_reached_(position)

        desc: A motor device called (name) reached position (position)
        (device)
        '''

        # disable motor
        self._stop_motor()

    def _stop_motor(self):
        if self.config['motor_left_output']:
            self.config['motor_left_output'].disable()

        if self.config['motor_right_output']:
            self.config['motor_right_output'].disable()

    def _ball_search_start(self, **kwargs):
        del kwargs
        self._stop_motor()
        # simply enable motor. will move to old position afterwards.
        if self.config['motor_left_output']:
            self.config['motor_left_output'].enable()
        else:
            self.config['motor_right_output'].enable()

    def _ball_search_stop(self, **kwargs):
        del kwargs
        # move to last position
        self._move_to_position(self._target_position)
