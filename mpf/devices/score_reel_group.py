"""A group of score reels."""
from collections import deque
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
        """Initialise score reel group."""
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

    def _initialize(self):
        self.reels = self.config['reels']
        self.reels.reverse()  # We want our smallest digit in the 0th element

        # ---- temp chimes code. todo move this --------------------
        self.config['chimes'].reverse()

        for i in range(len(self.config['chimes'])):

            if self.config['chimes'][i]:
                self.machine.events.add_handler(event='reel_' +
                                                      self.reels[
                                                          i].name + '_advance',
                                                handler=self.chime,
                                                chime=self.config['chimes'][i])
        # ---- temp chimes code end --------------------------------

        # register for events
        self.machine.events.add_handler('init_phase_4',
                                        self.initialize)

        self._tick_task = self.machine.clock.schedule_interval(self.tick, 0.01)

        # Need to hook this in case reels aren't done when ball ends
        self.machine.events.add_handler('ball_ending', self._ball_ending, 900)

    # ----- temp method for chime ------------------------------------
    @classmethod
    def chime(cls, chime):
        """Pulse chime."""
        chime.pulse()

    # ---- temp chimes code end --------------------------------------

    @property
    def assumed_value_list(self):
        """Return list that holds the values of the reels in the group."""
        value_list = []
        for reel in self.reels:
            if reel:
                value_list.append(reel.assumed_value)
                # Used lambda above so this list will always lookup the latest
            else:
                value_list.append(None)
        return value_list

    @property
    def assumed_value_int(self):
        """Return integer representation of the value we assume is shown on this ScoreReelGroup.

        A value of -999 means the value is unknown.
        """
        return self.reel_list_to_int(self.assumed_value_list)

    def initialize(self):
        """Initialize the score reels by reading their current physical values and setting each reel's rollover reel.

        This is a separate method since it can't run int __iniit__() because all the other reels have to be setup first.
        """
        self.get_physical_value_list()
        self.set_rollover_reels()

    def set_rollover_reels(self):
        """Call each reel's `set_rollover_reel` method and passes it a pointer to the next higher up reel.

        This is how we know whether we're able to advance the next higher up reel when a particular reel rolls
        over during a step advance.
        """
        for reel in range(len(self.reels)):
            if self.reels[reel] and (reel < len(self.reels) - 1):
                self.reels[reel].set_rollover_reel(self.reels[reel + 1])

    def tick(self, dt):
        """Automatically called once per machine tick and checks to see if there are any jumps or advances in progress.

        If so, calls those methods.
        """
        del dt
        if self.jump_in_progress:
            self._jump_advance_step()
        elif self.advance_queue:
            self._step_advance_step()
        elif not self.valid:
            self.validate()

    def is_desired_valid(self, notify_event=False):
        """Test to see whether the machine thinks the ScoreReelGroup is currently showing the desired value.

        In other words, is the ScoreReelGroup "done" moving? Note this ignores placeholder non-controllable digits.

        Returns: True or False
        """
        for i in range(len(self.reels)):
            if self.reels[i]:
                if self.assumed_value_list[i] != self.desired_value_list[i]:
                    if notify_event:
                        self.machine.events.post('reel_' +
                                                 self.reels[i].name +
                                                 '_resync')
                    return False

        '''event: reel_(name)_resync
        desc: The score reel (name) is not valid and will be resyncing.
        '''

        return True

    def get_physical_value_list(self):
        """Query all the reels in the group and builds a list of their actual current physical state.

        This is either the value of the current switch or -999 if no switch is active. This method also updates each
        reel's physical value.

        Returns: List of physical reel values.
        """
        output_list = []
        for reel in self.reels:
            if reel:
                output_list.append(reel.check_hw_switches())

        return output_list

    def validate(self, value=None):
        """Validate that this score reel group is in the position the machine wants it to be in.

        If lazy or strict confirm is enabled, this method will also make sure
        the reels are in their proper physical positions.

        Args:
            value (ignored): This method takes an argument of `value`, but
                it's not used. It's only there because when reels post their
                events after they're done moving, they include a parameter of
                `value` which is the position they're in. So we just need to
                have this argument listed so we can use this method as an event
                handler for those events.
        """
        del value

        self.log.debug("Checking to see if score reels are valid.")

        # Can't validate until the reels are done moving. This shouldn't happen
        # but we look for it just in case.
        if self.jump_in_progress or self.advance_queue:
            return False

        # If any reels are set to lazy or strict confirm, we're only going to
        # validate if they've hw_confirmed
        for reel in self.reels:

            if reel and (reel.config['confirm'] == 'lazy' or reel.config['confirm'] == 'strict') and not reel.hw_sync:
                return False  # need hw_sync to proceed

        self.log.debug("Desired list: %s", self.desired_value_list)
        self.log.debug("Assumed list: %s", self.assumed_value_list)
        self.log.debug("Assumed integer: %s", self.assumed_value_int)

        try:
            self.log.debug("Player's Score: %s", self.machine.game.player.score)
        except AttributeError:
            pass

        # todo if confirm is set to none, should we at least wait until the
        # coils are not energized to validate?

        if not self.is_desired_valid(notify_event=True):
            # FYI each reel will hw check during hw_sync, so if there's a
            # misfire that we can know about then it will be caught here
            self.machine.events.post('scorereelgroup_' + self.name + '_resync')
            '''event: scorereelgroup_(name)_resync
            desc: The score reel group (name) is not valid and will be
            resyncing.
            '''
            self.set_value(value_list=self.desired_value_list)
            return False

        self.valid = True
        self.machine.events.post('scorereelgroup_' + self.name + '_valid',
                                 value=self.assumed_value_int)
        '''event: scorereelgroup_(name)_valid
        desc: The score reall group (name) is valid.
        args:
        value: The integer value this score reel group is assumed to be at.
        '''

        if self.wait_for_valid_queue:
            self.log.debug("Found a wait queue. Clearing now.")
            self.wait_for_valid_queue.clear()
            self.wait_for_valid_queue = None

        return True

    def add_value(self, value, jump=False, target=None):
        """Add value to a ScoreReelGroup.

        You can also pass a negative value to subtract points.

        You can control the logistics of how these pulses are applied via the
        `jump` parameter. If jump is False (default), then this method will
        respect the proper "sequencing" of reel advances. For example, if the
        current value is 1700 and the new value is 2200, this method will fire
        the hundreds reel twice (to go to 1800 then 1900), then on the third
        pulse it will fire the thousands and hundreds (to go to 2000), then do
        the final two pulses to land at 2200.

        Args:
            value: The integer value you'd like to add to (or subtract
                from) the current value

            jump: Optional boolean value which controls whether the reels should
                "count up" to the new value in the classic EM way (jump=False)
                or whether they should just jump there as fast as they can
                (jump=True). Default is False.
            target: Optional integer that's the target for where this reel group
                should end up after it's done advancing. If this is not
                specified then the target value will be calculated based on the
                current reel positions, though sometimes this get's wonky if the
                reel is jumping or moving, so it's best to specify the target if
                you can.
        """
        self.log.debug("Adding '%s' to the displayed value. Jump=%s", value,
                       jump)

        # As a starting point, we'll base our assumed current value of the reels
        # based on whatever the machine thinks they are. This is subject to
        # change, which is why we use our own variable here.
        current_reel_value = self.assumed_value_int

        if self.jump_in_progress:
            self.log.debug("There's a jump in progress, so we'll just change "
                           "the target of the jump to include our values.")
            # We'll base our desired value off whatever the reel is advancing
            # plus our value, because since there's a jump in progress we have
            # no idea where the reels are at this exact moment
            current_reel_value = self.reel_list_to_int(self.desired_value_list)
            jump = True

        if current_reel_value == - 999:
            self.log.debug("Current displayed value is unkown, "
                           "so we're jumping to the new value.")
            current_reel_value = 0
            jump = True

        # If we have a target, yay! (And thank you to whatever called this!!)
        # If not we have to use our current_reel_value as the baseline which is
        # fine, but it makes a lot of assumptions
        if target is None:
            target = current_reel_value + value

        elif value < 0:
            self.log.debug("add_value is negative, so we're subtracting this "
                           "value. We will do this via a jump.")
            jump = True

        # If we have to jump to this new value (for whatever reason), go for it
        if jump:
            self.set_value(target)

        # Otherwise we can do the cool step-wise advance
        else:
            self.desired_value_list = self.int_to_reel_list(target)
            self._step_advance_add_steps(value)

    def set_value(self, value=None, value_list=None):
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
            value: An integer value of what the new displayed value (i.e. score)
                should be. This is the default option if you only pass a single
                positional argument, e.g. `set_value(2100)`.
            value_list: A list of the value you'd like the reel group to
                display.
        """
        if value is None and value_list is None:
            return  # we can't do anything here if we don't get a new value

        if value_list is None:
            value_list = self.int_to_reel_list(value)

        self.log.debug("Jumping to %s.", value_list)

        # set the new desired value which we'll use to verify the reels land
        # where we want them to.
        self.desired_value_list = value_list
        self.log.debug("set_value() just set DVL to: %s",
                       self.desired_value_list)

        self._jump_advance_step()

    def _jump_advance_step(self):
        # Checks the assumed values of the reels in the group, and if they're
        # off will automatically correct them.

        self.jump_in_progress = True
        self.valid = False

        if self.is_desired_valid():
            self.log.debug("They match! Jump is done.")
            self._jump_advance_complete()
            return

        reels_needing_advance = []  # reels that need to be advanced
        num_energized = 0  # count of the number of coils currently energized
        current_time = self.machine.clock.get_time()  # local reference for speed
        # loop through the reels one by one
        for i in range(len(self.reels)):
            this_reel = self.reels[i]  # local reference for speed
            if this_reel:

                # While we're in here let's get a count of the total number
                # of reels that are energized
                if this_reel.config['coil_inc'].time_when_done > current_time:
                    num_energized += 1

                # Does this reel want to be advanced, and is it ready?
                if self.desired_value_list[i] != self.assumed_value_list[i] and this_reel.ready:
                    # Do we need (and have) hw_sync to advance this reel?

                    if self.assumed_value_list[i] == -999 or this_reel.config['confirm'] == 'strict':

                        if this_reel.hw_sync:
                            reels_needing_advance.append(this_reel)

                    elif this_reel.ready:
                        reels_needing_advance.append(this_reel)

        # How many reels can we advance now?
        coils_this_round = (self.config['max_simultaneous_coils'] -
                            num_energized)

        # sort by last firing time, oldest first (so those are fired first)
        reels_needing_advance.sort(key=lambda x: x.next_pulse_time)

        if len(reels_needing_advance) < coils_this_round:
            coils_this_round = len(reels_needing_advance)

        for i in range(coils_this_round):
            reels_needing_advance[i].advance()

            # Any leftover reels that don't get fired this time will get picked up
            # whenever the next reel changes state and this method is called again.

    def _jump_advance_complete(self):
        # Called when a jump advance routine is complete and the score reel
        # group has been validated.

        self.log.debug("Jump complete")
        self.log.debug("Assumed values: %s", self.assumed_value_list)
        self.log.debug("Desired values: %s", self.desired_value_list)

        self.jump_in_progress = False

    def _step_advance_add_steps(self, value):
        # Receives an integer value, converts it to steps, adds them to the
        # step queue, and kicks off the step advance process. For example,
        # adding a value of 210 would result the following items added to the
        # advance queue: [coil_10, coil_100, coil_100]

        value_list = self.int_to_reel_list(value)

        self.log.debug("Will add '%s' to this reel group", value)

        for position, value in enumerate(value_list):
            if value:
                for dummy_num in range(value):
                    self.advance_queue.append(self.reels[position])

        # if there's a jump in progress we don't want to step on it, so we'll
        # just do nothing more here and _step_advance_step will be called when
        # the jump is done since we have entries in the advance queue
        if not self.jump_in_progress:
            self._step_advance_step()

    def _step_advance_step(self):
        # Attempts to kick off any advances that are in the advance_queue, but
        # that's not also possible. (For example, all the reels might be busy.)

        # todo if reel status is bad, do something

        if not self.advance_queue:
            self.validate()
            return

        self.valid = False

        # set our working reel to be the next one in the queue
        reel = self.advance_queue[0]

        # Check to see if this reel is ready. "Ready" depends on whether we're
        # using strict confirmation or not.

        # todo what if the hw is -999. Then we should return if we don't have
        # hw_sync also, right?

        if reel.config['confirm'] == 'strict' and not reel.hw_sync:
            return
        elif not reel.ready:
            return

        # is this real going to need a buddy pulse?
        self.log.debug("Reel: %s, Limit: %s, Current assumed value: %s",
                       reel.name, reel.config['limit_hi'], reel.assumed_value)
        if (reel.config['limit_hi'] == reel.assumed_value and
                not reel.rollover_reel_advanced):
            buddy_pulse = True
            # track that we've already ordered the buddy pulse so it doesn't
            # happen twice if this reel can't fire now for some reason
            reel.rollover_reel_advanced = True
            self.log.debug("Setting buddy pulse")
        else:
            buddy_pulse = False

        # todo we may not need the rollover_reel_advanced tracker anymore since
        # we wrapped the reel.advance below in an if block.

        # remove this reel from our queue from the queue
        self.advance_queue.popleft()

        # try to advance the reel, We use `if` here so this code block only runs
        # if the reel accepted our advance request
        if reel.advance():
            self.log.debug("Reel '%s' accepted advance", reel.name)
            self.log.debug("Reels (assumed): %s", self.assumed_value_int)
            try:
                self.log.debug("Score: %s",
                               self.machine.game.player.score)
            except AttributeError:
                pass
            self.machine.events.post('reel_' + reel.name + "_advance")
            # todo should this advance event be posted here? Or by the reel?
            '''event: reel_(name)_advance
            desc: The score reel (name) is advancing.
            '''

            # Add the reel's buddy to the advance queue
            if buddy_pulse:
                # insert the rollover reel
                if reel.rollover_reel:
                    self.advance_queue.appendleft(reel.rollover_reel)
                    # run through this again now so we pulse the buddy reel
                    # immediately (assuming we don't have too many pulsing
                    # currently, etc.)
                    self._step_advance_step()
                else:
                    # whoops, we don't have a rollover reel. Yay for player!
                    self.machine.events.post('scorereelgroup_' + self.name +
                                             '_rollover')
                    '''event: scorereelgroup_(name)_rollover
                    desc: The score reel group (name) has just rolled over,
                    meaning it exceeded its mechanical limit and rolled over
                    past zero.'''

        else:  # the reel did not accept the advance. Put it back in the queue
            self.advance_queue.appendleft(reel)
            self.log.debug("Reel '%s' rejected advance. We'll try again.",
                           reel.name)

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
            value: The interger value you'd like to convert.

        Returns:
            A list containing the values for each corresponding score reel,
            with the lowest reel digit position in list position 0.

        """
        if value == -999:
            value = 0
            # todo hack

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

    @classmethod
    def reel_list_to_int(cls, reel_list):
        """Convert an list of integers to a single integer.

        This method is like `int_to_reel_list` except that it works in the
        opposite direction.

        The list inputted is expected to be in "reverse" order, with the ones
        digit in the [0] index position. Values of `None` are converted to
        zeros. For example, if you pass `[None, 0, 3, 2, 1]`, this method will
        return an integer value of `12300`.

        Note this method does not take into consideration how many reel
        positions are in this ScoreReelGroup. It just converts whatever you
        pass it.

        Args:
            reel_list: The list containing the values for each score reel
                position.

        Returns:
            The resultant integer based on the list passed.
        """
        # reverse the list so it's in normal order
        reel_list.reverse()
        output = ""

        for item in reel_list:
            if isinstance(item, int):
                if item == -999:  # if any reels are unknown, then our int
                    return -999  # is unkown too.
                else:
                    output += str(item)
            elif isinstance(item, str) and item.isdigit():
                # Just in case we have an number that's a string
                output += str(int(item))  # ensure no leading zeros
            else:
                output += "0"
        return int(output)

    def light(self, relight_on_valid=False, **kwargs):
        """Light up this ScoreReelGroup based on the 'light_tag' in its config."""
        del kwargs
        self.log.debug("Turning on Lights")
        for light in self.machine.lights.items_tagged(
                self.config['lights_tag']):
            light.on()

        # Watch for these reels going out of sync so we can turn off the lights
        # while they're resyncing

        self.unlight_on_resync_key = self.machine.events.add_handler(
            'scorereelgroup_' + self.name + '_resync',
            self.unlight,
            relight_on_valid=True)

        if relight_on_valid:
            self.machine.events.remove_handler_by_key(self.light_on_valid_key)

    def unlight(self, relight_on_valid=False, **kwargs):
        """Turn off the lights for this ScoreReelGroup based on the 'light_tag' in its config."""
        del kwargs
        self.log.debug("Turning off Lights")
        for light in self.machine.lights.items_tagged(
                self.config['lights_tag']):
            light.off()

        if relight_on_valid:
            self.light_on_valid_key = self.machine.events.add_handler(
                'scorereelgroup_' + self.name + '_valid',
                self.light,
                relight_on_valid=True)
        elif self.unlight_on_resync_key:
            self.machine.events.remove_handler_by_key(
                self.unlight_on_resync_key)

    def _ball_ending(self, queue=None):
        # We need to hook the ball_ending event in case the ball ends while the
        # score reel is still catching up.

        # only do this if this is the active group
        if self.machine.score_reel_controller.active_scorereelgroup != self:
            return

        if not self.valid:
            self.log.debug("Score reel group is not valid. Setting a queue")
            self.wait_for_valid_queue = queue
            self.wait_for_valid_queue.wait()
        else:
            self.log.debug("Score reel group is valid. No queue needed.")
