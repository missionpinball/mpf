"""Hold coil ejector."""
from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector


class HoldCoilEjector(BallDeviceEjector):

    """Hold balls by enabling and releases by disabling a coil."""

    __slots__ = ["hold_release_in_progress"]

    def eject_all_balls(self):
        """Eject all balls."""
        raise NotImplementedError()

    def __init__(self, config, ball_device, machine):
        """Initialise hold coil ejector."""
        for option in ["hold_switches", "hold_coil", "hold_coil_release_time", "hold_events"]:
            if option not in config and option in ball_device.config:
                config[option] = ball_device.config[option]
        super().__init__(config, ball_device, machine)
        self.hold_release_in_progress = False

        self.config = self.machine.config_validator.validate_config("ball_device_ejector_hold", self.config)

        # handle hold_coil activation when a ball hits a switch
        for switch in self.config['hold_switches']:
            if '{}_active'.format(self.ball_device.config['captures_from'].name) in switch.tags:
                self.ball_device.raise_config_error(
                    "Ball device '{}' uses switch '{}' which has a "
                    "'{}_active' tag. This is handled internally by the device. Remove the "
                    "redundant '{}_active' tag from that switch.".format(
                        self.ball_device.name, switch.name, self.ball_device.config['captures_from'].name,
                        self.ball_device.config['captures_from'].name), 13)

            self.ball_device.machine.switch_controller.add_switch_handler_obj(
                switch=switch, state=1,
                ms=0,
                callback=self.hold)

        for event in self.config["hold_events"]:
            self.machine.events.add_handler(event, self.hold)

    async def eject_one_ball(self, is_jammed, eject_try, balls_in_device):
        """Eject one ball by disabling hold coil."""
        del balls_in_device
        # TODO: wait for some time to allow balls to settle for
        #       both entrance and after a release
        self._disable_hold_coil()
        self.hold_release_in_progress = True

        # allow timed release of single balls and reenable coil after
        # release. Disable coil when device is empty
        self.ball_device.delay.add(name='hold_coil_release',
                                   ms=self.config['hold_coil_release_time'],
                                   callback=self._hold_release_done)
        # TODO: support ejecting a single ball by checking the ball_counter

    async def reorder_balls(self):
        """Do nothing."""
        # TODO: disable coil for a short period

    def _disable_hold_coil(self):
        self.config['hold_coil'].disable()
        self.ball_device.debug_log("Disabling hold coil. New "
                                   "balls: %s.", self.ball_device.balls)

    def hold(self, **kwargs):
        """Event handler for hold event."""
        del kwargs
        # do not enable coil when we are ejecting
        if self.hold_release_in_progress:
            return

        self._enable_hold_coil()

    def _enable_hold_coil(self):
        self.config['hold_coil'].enable()
        self.ball_device.debug_log("Enabling hold coil. New "
                                   "balls: %s.", self.ball_device.balls)

    def _hold_release_done(self):
        self.hold_release_in_progress = False
        self.ball_device.log.debug("No more balls. Hold coil will stay disabled.")

        # reenable hold coil if there are balls left
        if self.ball_device.balls > 0:
            self._enable_hold_coil()

    def ball_search(self, phase, iteration):
        """Run ball search."""
        self.config['hold_coil'].pulse()
        return True
