"""Motor device."""
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.system_wide_device import SystemWideDevice


@DeviceMonitor(_move_direction="move_direction", _target_position="target_position", _last_position="last_position")
class Motor(SystemWideDevice):

    """A motor which can be controlled using drivers."""

    __slots__ = ["_target_position", "_last_position", "type", "_move_direction"]

    config_section = 'motors'
    collection = 'motors'
    class_label = 'motor'

    def __init__(self, machine, name):
        """Initialise motor."""
        self._target_position = None
        self._last_position = None
        self.type = None
        self._move_direction = "stopped"
        super().__init__(machine, name)

    async def _initialize(self):
        await super()._initialize()
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
        else:
            self.type = "one_direction"

        for position, switch in self.config['position_switches'].items():
            self.machine.switch_controller.add_switch_handler_obj(switch, self._update_position,
                                                                  callback_kwargs={"position": position})

        # add handlers
        for event, position in self.config['go_to_position'].items():
            if position not in self.config['position_switches']:
                self.raise_config_error("Invalid position {} in go_to_position".format(position), 4)
            self.machine.events.add_handler(event, self.event_go_to_position, position=position)

        if self.config['include_in_ball_search']:
            self.machine.events.add_handler("ball_search_started",
                                            self._ball_search_start)
            self.machine.events.add_handler("ball_search_stopped",
                                            self._ball_search_stop)

    def _validate_last_position(self) -> bool:
        """Verify that at most one position switch is active."""
        active_position_switches = [(position, switch) for position, switch in
                                    self.config['position_switches'].items() if switch.state]
        if len(active_position_switches) > 1:
            self.warning_log("Found %s active position switches: %s. There should be only one position switch active "
                             "at a time.", len(active_position_switches),
                             active_position_switches)
            self.machine.service.add_technical_alert(
                self, "Multiple position switches are active: {}. Verify switches.".format(active_position_switches))
            return False

        return True

    @event_handler(1)
    def event_reset(self, **kwargs):
        """Event handler for reset event."""
        del kwargs
        self. reset()

    def reset(self):
        """Go to reset position."""
        self.go_to_position(self.config['reset_position'])

    @event_handler(10)
    def event_go_to_position(self, position=None, **kwargs):
        """Event handler for go_to_position event."""
        del kwargs
        if position is None:
            raise AssertionError("Got go_to_position event without position.")

        self.go_to_position(position)

    def go_to_position(self, position):
        """Move motor to a specific position."""
        self.log.info("Moving motor to position %s", position)
        self._target_position = position
        self._move_to_position(position)

    def _move_to_position(self, position):
        if not self._validate_last_position():
            self.warning_log("Will not move motor because multiple position switches are active.")
            self._stop_motor()
            return

        switch = self.config['position_switches'][position]
        # check if we are already in this position
        if self.machine.switch_controller.is_active(switch):
            # already in position
            self._reached_position(position)
            self._stop_motor()
        else:
            if self.type == "two_directions":
                if self._last_position:
                    assumed_position = self._last_position
                else:
                    active_position_switches = [position for position, switch in
                                                self.config['position_switches'].items()
                                                if switch.state]
                    if len(active_position_switches) == 1:
                        assumed_position = active_position_switches[0]
                        self.debug_log("Assuming position based on switches to be %s", assumed_position)
                    else:
                        assumed_position = None

                if assumed_position is None and \
                        list(self.config['position_switches']).index(self.config['reset_position']) == 0:
                    self._move_left()
                elif assumed_position is None:
                    self._move_right()
                elif list(self.config['position_switches']).index(assumed_position) > \
                        list(self.config['position_switches']).index(position):
                    self._move_left()
                else:
                    self._move_right()
            else:
                # not in position. start motor
                if self.config['motor_left_output']:
                    self._move_left()
                else:
                    self._move_right()

    def _update_position(self, position, **kwargs):
        """Handle that motor reached a certain position."""
        del kwargs
        first_known_position = self._last_position is None
        if not self._validate_last_position():
            self.warning_log("Will stop motor because multiple position switches are active.")
            self._stop_motor()
            self._last_position = None
            return

        self._last_position = position

        if position == self._target_position:
            self._reached_position(position)
        else:
            self.debug_log("Motor is at position %s", position)

            if self.type == "two_directions":
                # special case: initial position has been unknown and we reached our first position
                # we might have moved in the wrong direction so correct this now
                if first_known_position and self._move_direction == "right" and \
                        list(self.config['position_switches']).index(self._last_position) > \
                        list(self.config['position_switches']).index(self._target_position):
                    self._move_left()
                elif first_known_position and self._move_direction == "left" and \
                        list(self.config['position_switches']).index(self._last_position) < \
                        list(self.config['position_switches']).index(self._target_position):
                    self._move_right()
                elif list(self.config['position_switches']).index(position) in \
                        (0, len(self.config['position_switches']) - 1):
                    self.warning_log("Motor hit end switch %s unexpectedly. Stopping motor.", position)
                    self._stop_motor()

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

        self._move_direction = "stopped"

    def _move_right(self):
        if self.config['motor_left_output']:
            self.config['motor_left_output'].disable()

        self.config['motor_right_output'].enable()
        self._move_direction = "right"

    def _move_left(self):
        if self.config['motor_right_output']:
            self.config['motor_right_output'].disable()

        self.config['motor_left_output'].enable()
        self._move_direction = "left"

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
