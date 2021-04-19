"""Enable/disable ejector."""
from mpf.devices.ball_device.ball_device_ejector import BallDeviceEjector

from mpf.core.delays import DelayManager
from mpf.devices.ball_device.default_ball_search import DefaultBallSearch


class EnableCoilEjector(DefaultBallSearch, BallDeviceEjector):

    """Enable a coil to eject one ball."""

    __slots__ = ["delay"]

    def __init__(self, config, ball_device, machine):
        """Initialise ejector."""
        for option in ["eject_coil", "eject_coil_enable_time"]:
            if option not in config and option in ball_device.config:
                config[option] = ball_device.config[option]

        super().__init__(config, ball_device, machine)
        self.delay = DelayManager(self.ball_device.machine)

        self.config = self.machine.config_validator.validate_config("ball_device_ejector_enable", self.config)

    async def eject_one_ball(self, is_jammed, eject_try, balls_in_device):
        """Enable eject coil."""
        del is_jammed
        del eject_try
        # If multiple eject_coil_enable_time values, they correspond to the # of balls
        if self.ball_device.balls <= len(self.config['eject_coil_enable_time']):
            eject_time = self.config['eject_coil_enable_time'][balls_in_device - 1]
        else:
            eject_time = self.config['eject_coil_enable_time'][-1]

        # default pulse
        self.ball_device.debug_log("Enabling eject coil for %sms, Current balls: %s.",
                                   eject_time,
                                   self.ball_device.balls)

        self.config['eject_coil'].enable(max_wait_ms=self.config['eject_coil_max_wait_ms'])
        self.delay.reset(name="disable", callback=self._disable_coil,
                         ms=eject_time)

    async def reorder_balls(self):
        """Reordering balls is not supported."""
        # TODO: implement
        self.ball_device.log.warning("Reordering balls is not implemented in enable ejector")

    def _disable_coil(self):
        """Disable the coil."""
        self.config['eject_coil'].disable()

    def _fire_coil_for_search(self, full_power):
        if not full_power:
            self.config['eject_coil'].pulse()
        else:
            self.config['eject_coil'].enable()
            self.delay.reset(name="disable", callback=self._disable_coil,
                             ms=self.config['eject_coil_enable_time'][0])
        return True
