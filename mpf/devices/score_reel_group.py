"""A group of score reels."""
from collections import deque

import asyncio

from mpf.core.system_wide_device import SystemWideDevice
from mpf.devices.score_reel_controller import ScoreReelController


class ScoreReelGroup(SystemWideDevice):

    """Represents a logical grouping of score reels in a pinball machine.

    Multiple individual ScoreReel object make up the individual digits of this
    group. This group also has support for the blank zero "inserts" that some
    machines use. This is a subclass of mpf.core.device.Device.
    """

    config_section = 'score_reel_groups'
    collection = 'score_reel_groups'
    class_label = 'score_reel_group'

    @classmethod
    def device_class_init(cls, machine):
        """If we have at least one score reel group, we need a ScoreReelController."""
        machine.score_reel_controller = ScoreReelController(machine)

    def __init__(self, machine, name):
        """initialize score reel group."""
        super().__init__(machine, name)

        self.wait_for_valid_queue = None
        self.valid = True  # Confirmed reels are showing the right values
        self.unlight_on_resync_key = None
        self.light_on_valid_key = None

        self.reels = []
        # A list of individual ScoreReel objects that make up this
        # ScoreReelGroup. The number of items in the list correspondis to the
        # number of digits that can be displayed. A value of `None` indicates a
        # position that is not controlled by a moving reel (like a fake ones
        # digit).

        # Note that this is "backwards," with element 0 representing the ones
        # digit, element 1 representing the tens, etc..

        self.desired_value_list = []
        # A list of what values the machine desires to have the score reel
        # group set to.

        self.advance_queue = deque()
        # Holds a list of the next reels that for step advances.

        self.jump_in_progress = False
        # Boolean attribute that is True when a jump advance is in progress.

        self._tick_task = None

    async def _initialize(self):
        await super()._initialize()
        self.reels = self.config['reels']
        self.reels.reverse()  # We want our smallest digit in the 0th element

        self.config['chimes'].reverse()
        for i in range(len(self.config['chimes'])):

            if self.config['chimes'][i]:
                if not self.reels[i]:
                    self.raise_config_error("Invalid reel for chime {}".format(self.config['chimes'][i]), 1)
                self.machine.events.add_handler(event='reel_' + self.reels[i].name + '_advancing',
                                                handler=self.chime,
                                                chime=self.config['chimes'][i])

    @classmethod
    def chime(cls, chime, **kwargs):
        """Pulse chime."""
        del kwargs
        chime.pulse()

    def set_value(self, value):
        """Reset the score reel group to display the value passed.

        This method will "jump" the score reel group to display the value
        that's passed as an it. (Note this "jump" technique means it will just
        move the reels as fast as it can, and nonsensical values might show up
        on the reel while the movement is in progress.)

        This method is used to "reset" a reel group to all zeros at the
        beginning of a game, and can also be used to reset a reel group that is
        confused or to switch a reel to the new player's score if multiple
        players a sharing the same reel group.

        Note you can choose to pass either an integer representation of the
        value, or a value list.

        Args:
        ----
            value: An integer value of what the new displayed value (i.e. score)
                should be. This is the default option if you only pass a single
                positional argument, e.g. `set_value(2100)`.
        """
        value_list = self.int_to_reel_list(value)

        self.log.debug("Jumping to %s.", value_list)

        # set the new desired value which we'll use to verify the reels land
        # where we want them to.
        self.desired_value_list = value_list

        # loop through the reels one by one
        for i in range(len(self.reels)):
            if not self.reels[i]:
                continue

            self.reels[i].set_destination_value(self.desired_value_list[i])

    def wait_for_ready(self):
        """Return a future which will be done when all reels reached their destination."""
        futures = []
        for reel in self.reels:
            if reel:
                futures.append(reel.wait_for_ready())

        return asyncio.wait(iter(futures))

    def int_to_reel_list(self, value):
        """Convert an integer to a list of integers that represent each positional digit in this ScoreReelGroup.

        The list returned is in reverse order. (See the example below.)

        The list returned is customized for this ScoreReelGroup both in terms
        of number of elements and values of `None` used to represent blank
        plastic zero inserts that are not controlled by a score reel unit.

        For example, if you have a 5-digit score reel group that has 4
        phyiscial reels in the tens through ten-thousands position and a fake
        plastic "0" insert for the ones position, if you pass this method a
        value of `12300`, it will return `[None, 0, 3, 2, 1]`

        This method will pad shorter ints with zeros, and it will chop off
        leading digits for ints that are too long. (For example, if you pass a
        value of 10000 to a ScoreReelGroup which only has 4 digits, the
        returns list would correspond to 0000, since your score reel unit has
        rolled over.)

        Args:
        ----
            value: The interger value you'd like to convert.

        Returns a list containing the values for each corresponding score reel,
        with the lowest reel digit position in list position 0.
        """
        output_list = []

        # convert our number to a string
        str_value = str(value)

        # pad the string with leading zeros
        str_value = str_value.zfill(len(self.reels))

        # slice off excess characters if the value is longer than num of reels

        # how many digits do we have to slice?
        trim = len(str_value) - len(self.reels)
        # and... slice!
        str_value = str_value[trim:]

        # todo if we don't do the above trim then it will just show the highest
        # digits, effective "shifting" the score by one. Might be a fun feature?

        # generate our list with one digit per item
        for digit in str_value:
            output_list.append(int(digit))

        # reverse the list so the least significant is first
        output_list.reverse()

        # replace fake position digits with `None`
        for i, dummy_output in enumerate(output_list):
            if not self.reels[i]:
                output_list[i] = None

        return output_list

    def light(self, **kwargs):
        """Light up this ScoreReelGroup based on the 'light_tag' in its config."""
        del kwargs
        self.log.debug("Turning on Lights")
        for light in self.machine.lights.items_tagged(
                self.config['lights_tag']):
            light.on()

    def unlight(self, **kwargs):
        """Turn off the lights for this ScoreReelGroup based on the 'light_tag' in its config."""
        del kwargs
        self.log.debug("Turning off Lights")
        for light in self.machine.lights.items_tagged(
                self.config['lights_tag']):
            light.off()
