"""Contains the base classes for mechanical EM-style score reels."""
import asyncio

from mpf.core.delays import DelayManager
from mpf.core.system_wide_device import SystemWideDevice


class ScoreReel(SystemWideDevice):

    """Represents an individual electro-mechanical score reel in a pinball machine.

    Multiples reels of this class can be grouped together into ScoreReelGroups
    which collectively make up a display like "Player 1 Score" or "Player 2
    card value", etc.

    This device class is used for all types of mechanical number reels in a
    machine, including reels that have more than ten numbers and that can move
    in multiple directions (such as the credit reel).
    """

    config_section = 'score_reels'
    collection = 'score_reels'
    class_label = 'score_reel'

    def __init__(self, machine, name):
        """Initialise score reel."""
        super().__init__(machine, name)
        self.delay = DelayManager(machine.delayRegistry)

        self.value_switches = []
        # This is a list with each element corresponding to a value on the
        # reel. An entry of None means there's no value switch there. An entry
        # of a reference to a switch object means there
        # is a switch there.

        self.hw_sync = False
        # Specifies whether this reel has verified it's positions via the
        # switches since it was last advanced."""

        self.ready = True
        # Whether this reel is ready to advance. Typically used to make sure
        # it's not trying to re-fire a stuck position.

        self.assumed_value = -999
        # The assumed value the machine thinks this reel is showing. A value
        # of -999 indicates that the value is unknown.

        self._destination_value = 0
        # Holds the index of the destination the reel is trying to advance to.

        self._runner = None
        # asyncio task which advances the reel

        self._busy = asyncio.Event(loop=self.machine.clock.loop)
        self._busy.set()
        # will be cleared when the runner is done. set to trigger the runner

        self._ready = asyncio.Event(loop=self.machine.clock.loop)
        # will be set when this real is ready and shows the destination value

        # stop device on shutdown
        self.machine.events.add_handler("shutdown", self.stop)

    def _initialize(self):
        self.log.debug("Configuring score reel with: %s", self.config)

        # figure out how many values we have
        # Add 1 so range is inclusive of the lower limit
        num_values = self.config['limit_hi'] - self.config['limit_lo'] + 1

        self.log.debug("Total reel values: %s", num_values)

        for value in range(num_values):
            self.value_switches.append(self.config.get('switch_' + str(value)))

        self._runner = self.machine.clock.loop.create_task(self._run())
        self._runner.add_done_callback(self._done)

    def stop(self, **kwargs):
        """Stop device."""
        del kwargs
        self._runner.cancel()

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def check_hw_switches(self):
        """Check all the value switches for this score reel.

        This check only happens if `self.ready` is `True`. If the reel is not
        ready, it means another advance request has come in after the initial
        one. In that case then the subsequent advance will call this method
        again when after that advance is done.

        If this method finds an active switch, it sets `self.physical_value` to
        that. Otherwise it sets it to -999. It will also update
        `self.assumed_value` if it finds an active switch. Otherwise it leaves
        that value unchanged.

        This method is automatically called (via a delay) after the reel
        advances. The delay is based on the config value
        `self.config['hw_confirm_time']`.

        TODO: What happens if there are multiple active switches? Currently it
        will return the highest one. Is that ok?
        """
        # check to make sure the 'hw_confirm_time' time has passed. If not then
        # we cannot trust any value we read from the switches

        self.log.debug("Checking hw switches to determine reel value with hw_confirm_time %sms",
                       self.config['hw_confirm_time'])
        for i in range(len(self.value_switches)):
            if self.value_switches[i]:  # not all values have a switch
                if self.machine.switch_controller.is_active(self.value_switches[i].name,
                                                            ms=self.config['hw_confirm_time']):
                    if self.assumed_value != i:
                        self.log.info("Setting value to %s because that switch is active.", i)
                        if self.assumed_value != -999:
                            self.log.warning("Reel desynced. Assumed: %s. Real: %s", self.assumed_value, i)

                        self.assumed_value = i

                    self.hw_sync = True
                    return

        # check if there is a switch for the current assumed_value
        if (self.assumed_value > 0 and self.value_switches[self.assumed_value] and
                not self.machine.switch_controller.is_active(self.value_switches[self.assumed_value].name,
                                                             ms=self.config['hw_confirm_time'])):
            self.log.warning("Resetting value because the switch for %s is not active.", self.assumed_value)
            self.assumed_value = -999
            self.hw_sync = False

    @asyncio.coroutine
    def _run(self):
        self.check_hw_switches()
        while True:
            yield from self._busy.wait()

            yield from self._advance_reel()

    @asyncio.coroutine
    def _advance_reel(self):
        self.log.debug("Advancing reel to value %s, current value %s", self._destination_value, self.assumed_value)
        while self._destination_value != self.assumed_value:
            wait_ms = self.config['coil_inc'].pulse(max_wait_ms=500)
            previous_value = self.assumed_value

            yield from asyncio.sleep((wait_ms + self.config['repeat_pulse_time']) / 1000, loop=self.machine.clock.loop)
            self.assumed_value += 1
            self.assumed_value %= len(self.value_switches)

            self.check_hw_switches()

            if previous_value != self.assumed_value and self.assumed_value > 0:
                self.machine.events.post('reel_' + self.name + "_advance")
            self.log.debug("Assumed value: %s", self.assumed_value)

        self._busy.clear()
        self._ready.set()
        self.log.debug("Advancing to %s successful.", self._destination_value)

    def wait_for_ready(self):
        """Return a future for ready."""
        return self._ready.wait()

    def set_destination_value(self, value):
        """Return the integer value of the destination this reel is moving to.

        Args:

        Returns: The value of the destination. If the current
            `self.assumed_value` is -999, this method will always return -999
            since it doesn't know where the reel is and therefore doesn't know
            what the destination value would be.
        """
        if self._destination_value != value:
            self.log.debug("Setting new score_reel value. Old destination value: %s, New destination value: %s",
                           self._destination_value, value)

            self._destination_value = value

            self._busy.set()
