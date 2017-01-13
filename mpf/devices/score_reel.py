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

        self.rollover_reel_advanced = False
        # True when a rollover pulse has been ordered

        self.value_switches = []
        # This is a list with each element corresponding to a value on the
        # reel. An entry of None means there's no value switch there. An entry
        # of a reference to a switch object (todo or switch name?) means there
        # is a switch there.
        self.num_values = 0
        # The number of values on this wheel. This starts with zero, so a
        # wheel with 10 values will have this value set to 9. (This actually
        # makes sense since most (all?) score reels also have a zero value.)

        self.physical_value = -999
        # The physical confirmed value of this reel. This will always be the
        # value of whichever switch is active or -999. This differs from
        # `self.assumed_value` in that assumed value will make assumptions about
        # where the reel is as it pulses through values with no swithces,
        # whereas this physical value will always be -999 if there is no switch
        # telling it otherwise.

        # Note this value will be initialized via self.check_hw_switches()
        # below.

        self.hw_sync = False
        # Specifies whether this reel has verified it's positions via the
        # switches since it was last advanced."""

        self.ready = True
        # Whether this reel is ready to advance. Typically used to make sure
        # it's not trying to re-fire a stuck position.

        self.assumed_value = -999
        # The assumed value the machine thinks this reel is showing. A value
        # of -999 indicates that the value is unknown.

        self.next_pulse_time = 0
        # The time when this reel next wants to be pulsed. The reel will set
        # this on its own (based on its own attribute of how fast pulses can
        # happen). If the ScoreReelController is ready to pulse this reel and
        # the value is in the past, it will do a pulse. A value of 0 means this
        # reel does not currently need to be pulsed.

        self.rollover_reel = None
        # A reference to the ScoreReel object of the next higher reel in the
        # group. This is used so the reel can notify its neighbor that it needs
        # to advance too when this reel rolls over.

        self._destination_index = 0
        # Holds the index of the destination the reel is trying to advance to.

        # todo add some kind of status for broken?

        self._runner = None

        self._busy = asyncio.Event(loop=self.machine.clock.loop)

    def _initialize(self):
        self.log.debug("Configuring score reel with: %s", self.config)

        # figure out how many values we have
        # Add 1 so range is inclusive of the lower limit
        self.num_values = self.config['limit_hi'] - self.config['limit_lo'] + 1

        self.log.debug("Total reel values: %s", self.num_values)

        for value in range(self.num_values):
            self.value_switches.append(self.config.get('switch_' + str(value)))

        self._runner = self.machine.clock.loop.create_task(self._run())
        self._runner.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        try:
            future.result()
        except asyncio.CancelledError:
            pass

    def set_rollover_reel(self, reel):
        """Set this reels' rollover_reel to the object of the next higher reel."""
        self.log.debug("Setting rollover reel: %s", reel.name)
        self.rollover_reel = reel

    def advance(self):
        """Perform the coil firing to advance this reel one position (up or down).

        This method also schedules delays to post the following events:

        `reel_<name>_ready`: When the config['repeat_pulse_time'] time is up
        `reel_<name>_hw_value`: When the config['hw_confirm_time'] time is up

        Args:

        Returns: If this method is unable to advance the reel (either because
            it's not ready, because it's at its maximum value and does not have
            rollover capabilities, or because you're trying to advance it in a
            direction but it doesn't have a coil for that direction), it will
            return `False`. If it's able to pulse the advance coil, it returns
            `True`.
        """
        self.log.debug("Received command advance Reel")

        self.set_destination_value()
        # above line also sets self._destination_index

        if self.next_pulse_time > self.machine.clock.get_time():
            # This reel is not ready to pulse again
            # Note we don't allow this to be overridden. Figure the
            # recycle time is there for a reason and we don't want to
            # potentially break an old delicate mechanism
            self.log.debug("Received advance request but this reel is not "
                           "ready")
            return False  # since we didn't advance...in case anyone cares?

        # Ensure we're not at the limit of a reel that can't roll over
        if not ((self.physical_value == self.config['limit_hi']) and not self.config['rollover']):
            self.log.debug("Ok to advance")

            # Since we're firing, assume we're going to make it
            self.assumed_value = self._destination_index
            self.log.debug("+++Setting assumed value to: %s",
                           self.assumed_value)

            # Reset our statuses (stati?) :)
            self.ready = False
            self.hw_sync = False

            # fire the coil
            self.config['coil_inc'].pulse(250)

            # set delay to notify when this reel can be fired again
            self.delay.add(name='ready_to_fire',
                           ms=self.config['repeat_pulse_time'],
                           callback=self._ready_to_fire)

            self.next_pulse_time = (self.machine.clock.get_time() +
                                    (self.config['repeat_pulse_time'] /
                                     1000.0))
            self.log.debug("@@@ New Next pulse ready time: %s",
                           self.next_pulse_time)

            # set delay to check the hw switches
            self.delay.add(name='hw_switch_check',
                           ms=self.config['hw_confirm_time'],
                           callback=self.check_hw_switches)

            return True

        else:
            self.log.warning("Received command to increment reel, but "
                             "we're at the max limit and this reel "
                             "cannot roll over")
            return False

    def _ready_to_fire(self):
        # automatically called (via a delay) after the reel fires to post an
        # event that the reel is ready to fire again
        self.ready = True
        self.machine.events.post('reel_' + self.name + "_ready")
        '''event: reel_(name)_ready
        desc: The score real (name) is ready to be pulsed again.'''

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

        self.log.debug("Checking hw switches to determine reel value")
        for i in range(len(self.value_switches)):
            if self.value_switches[i]:  # not all values have a switch
                if self.machine.switch_controller.is_active(self.value_switches[i].name):
                    if self.assumed_value != i:
                        self.log.info("Setting value to %s because that switch is active.", i)
                        self.assumed_value = i
                    self.hw_sync = True
                    return

        # check if there is a switch for the current assumed_value
        if (self.assumed_value in self.value_switches and self.value_switches[self.assumed_value] and
                not self.machine.switch_controller.is_active(self.value_switches[self.assumed_value].name)):
            self.log.info("Resetting value because the switch for %s is not active.", self.assumed_value)
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
        self.log.debug("Advancing reel to index %s, current index %s", self._destination_index, self.assumed_value + 1)
        while self._destination_index != self.assumed_value + 1:
            wait_ms  = self.config['coil_inc'].pulse(max_wait_ms=500)

            yield from asyncio.sleep((wait_ms + self.config['repeat_pulse_time']) / 1000, loop=self.machine.clock.loop)
            self.assumed_value += 1
            self.assumed_value %= len(self.value_switches)

            self.check_hw_switches()

        self._busy.clear()
        self.log.debug("Advancing to %s successful.", self._destination_index)

    def set_destination_value(self, value):
        """Return the integer value of the destination this reel is moving to.

        Args:

        Returns: The value of the destination. If the current
            `self.assumed_value` is -999, this method will always return -999
            since it doesn't know where the reel is and therefore doesn't know
            what the destination value would be.
        """
        if self._destination_index != value + 1:
            self.log.debug("Setting new score_reel value. Old destination_index: %s, New destination_index: %s",
                           self._destination_index, value + 1)

            self._destination_index = value + 1

            self._busy.set()

