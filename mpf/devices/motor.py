"""Motor device."""
from mpf.core.system_wide_device import SystemWideDevice


class Motor(SystemWideDevice):

    """A motor which can be controlled using drivers."""

    config_section = 'motors'
    collection = 'motors'
    class_label = 'motor'

    def _initialize(self):
        super()._initialize()
        if self.config['reset_position'] not in self.config['position_switches']:
            raise AssertionError("Invalid reset position")

        # add handlers
        for event, position in self.config['go_to_position'].items():
            if position not in self.config['position_switches']:
                raise AssertionError("Invalid position {} in go_to_position".format(position))
            self.machine.events.add_handler(event, self.go_to_position, position=position)

    def reset(self, **kwargs):
        """Go to reset position."""
        del kwargs
        self.go_to_position(self.config['reset_position'])

    def go_to_position(self, position):
        """Move motor to a specific position."""
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
        """Called when motor reached a certain position."""
        del kwargs
        self.log.info("Motor is in position %s", position)

        self.machine.events.post("motor_{}_reached_{}".format(self.name, position))
        '''event: motor_(name)_reached_(position)

        desc: A motor device called (name) reached position (position)
        (device)
        '''

        # disable motor
        self.config['motor_coil'].disable()
