"""Enable/disable ejector."""
import asyncio

from mpf.devices.ball_device.pulse_coil_ejector import PulseCoilEjector

from mpf.core.delays import DelayManager


class EnableCoilEjector(PulseCoilEjector):

    """Enable a coil to eject one ball."""

    __slots__ = ["delay"]

    def __init__(self, config, ball_device, machine):
        """Initialise ejector."""
        super().__init__(config, ball_device, machine)
        self.delay = DelayManager(self.ball_device.machine.delayRegistry)

    def _validate_config(self):
        # overwrite validation from pulse_coil_ejector
        pass

    @asyncio.coroutine
    def eject_one_ball(self, is_jammed, eject_try):
        """Enable eject coil."""
        del is_jammed
        del eject_try

        # If multiple eject_coil_enable_time values, they correspond to the # of balls
        if self.ball_device.balls <= len(self.ball_device.config['eject_coil_enable_time']):
            eject_time = self.ball_device.config['eject_coil_enable_time'][self.ball_device.balls - 1]
        else:
            eject_time = self.ball_device.config['eject_coil_enable_time'][-1]

        # default pulse
        self.ball_device.debug_log("Enabling eject coil for %sms, Current balls: %s.",
                                   eject_time,
                                   self.ball_device.balls)

        self.ball_device.config['eject_coil'].enable()
        self.delay.reset(name="disable", callback=self._disable_coil,
                         ms=eject_time)

    def _disable_coil(self):
        """Disable the coil."""
        self.ball_device.config['eject_coil'].disable()

    def _fire_coil_for_search(self, full_power):
        if full_power and self.ball_device.config['eject_coil_jam_pulse']:
            self.ball_device.config['eject_coil'].pulse()
        else:
            self.ball_device.config['eject_coil'].enable()
            self.delay.reset(name="disable", callback=self._disable_coil,
                             ms=self.ball_device.config['eject_coil_enable_time'][0])
        return True
