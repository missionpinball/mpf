""" Contains the base classes for mechanical EM-style score reels."""
# score_reel.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time

from collections import deque
from mpf.system.device import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing
from mpf.system.config import Config


# Known limitations of this module:
# Assumes all score reels include a zero value
# Assumes all score reels count up or down by one
# Assumes all score reels map their displayed value to their stored value
# in a 1:1 way. (i.e. value[0] displays 0, value[5] displays 5, etc.

# Note, currently this module only supports "incrementing" reels (i.e. counting
# up). Decrementing support will be added in the future


class ScoreReelController(object):
    """The overall controller that is in charge of and manages the score reels
    in a pinball machine.

    The main thing this controller does is keep track of how many
    ScoreReelGroups there are in the machine and how many players there are,
    as well as maps the current player to the proper score reel.

    This controller is also responsible for working around broken
    ScoreReelGroups and "stacking" and switching out players when there are
    multiple players per ScoreReelGroup.

    """

    def __init__(self, machine):
        self.machine = machine
        self.log = logging.getLogger("ScoreReelController")
        self.log.debug("Loading the ScoreReelController")

        self.active_scorereelgroup = None
        """Pointer to the active ScoreReelGroup for the current player.
        """
        self.player_to_scorereel_map = []
        """This is a list of ScoreReelGroup objects which corresponds to player
        indexes. The first element [0] in this list is the first player (which
        is player index [0], the next one is the next player, etc.
        """
        self.reset_queue = []
        """List of score reel groups that still need to be reset"""
        self.queue = None
        """Holds any active queue event queue objects"""

        # register for events

        # switch the active score reel group and reset it (if needed)
        self.machine.events.add_handler('player_turn_start',
                                        self.rotate_player)

        # receive notification of score changes
        self.machine.events.add_handler('score_change', self.score_change)

        # receives notifications of game starts to reset the reels
        self.machine.events.add_handler('game_starting', self.game_starting)

    def rotate_player(self, **kwargs):
        """Called when a new player's turn starts.

        The main purpose of this method is to map the current player to their
        ScoreReelGroup in the backbox. It will do this by comparing length of
        the list which holds those mappings (`player_to_scorereel_map`) to
        the length of the list of players. If the player list is longer that
        means we don't have a ScoreReelGroup for that player.

        In that case it will check the tags of the ScoreReelGroups to see if
        one of them is tagged with playerX which corresponds to this player.
        If not then it will pick the next free one. If there are none free,
        then it will "double up" that player on an existing one which means
        the same Score Reels will be used for both players, and they will
        reset themselves automatically between players.
        """

        # if our player to reel map is less than the number of players, we need
        # to create a new mapping
        if (len(self.player_to_scorereel_map) <
                len(self.machine.game.player_list)):
            self.map_new_score_reel_group()

        self.active_scorereelgroup = self.player_to_scorereel_map[
            self.machine.game.player.index]

        self.log.debug("Mapping Player %s to ScoreReelGroup '%s'",
                       self.machine.game.player.number,
                       self.active_scorereelgroup.name)

        # Make sure this score reel group is showing the right score
        self.log.debug("Current player's score: %s",
                       self.machine.game.player.score)
        self.log.debug("Score displayed on reels: %s",
                       self.active_scorereelgroup.assumed_value_int)
        if (self.active_scorereelgroup.assumed_value_int !=
                self.machine.game.player.score):
            self.active_scorereelgroup.set_value(
                self.machine.game.player.score)

        # light up this group
        for group in self.machine.score_reel_groups:
            group.unlight()

        self.active_scorereelgroup.light()

    def map_new_score_reel_group(self):
        """Creates a mapping of a player to a score reel group."""

        # do we have a reel group tagged for this player?
        for reel_group in self.machine.score_reel_groups.items_tagged(
                        "player" + str(self.machine.game.player.number)):
            self.player_to_scorereel_map.append(reel_group)
            self.log.debug("Found a mapping to add: %s", reel_group.name)
            return

        # if we didn't find one, then we'll just use the first player's group
        # for all the additional ones.

        # todo maybe we should get fancy with looping through? Meh... we'll
        # cross that bridge when we get to it.

        self.player_to_scorereel_map.append(self.player_to_scorereel_map[0])

    def score_change(self, score, change):
        """Called whenever the score changes and adds the score increase to the
        current active ScoreReelGroup.

        This method is the handler for the score change event, so it's called
        automatically.

        Args:
            score: Integer value of the new score. This parameter is ignored,
                and included only because the score change event passes it.
            change: Interget value of the change to the score.
        """
        self.active_scorereelgroup.add_value(value=change, target=score)

    def game_starting(self, queue, game):
        """Resets the score reels when a new game starts.

        This is a queue event so it doesn't allow the game start to continue
        until it's done.

        Args:
            queue: A reference to the queue object for the game starting event.
            game: A reference to the main game object. This is ignored and only
                included because the game_starting event passes it.
        """
        self.queue = queue
        # tell the game_starting event queue that we have stuff to do
        self.queue.wait()

        # populate the reset queue
        self.reset_queue = []

        for player, score_reel_group in self.machine.score_reel_groups.iteritems():
            self.reset_queue.append(score_reel_group)
        self.reset_queue.sort(key=lambda x: x.name)
        # todo right now this sorts by ScoreGroupName. Need to change to tags
        self._reset_next_group()  # kick off the reset process

    def _reset_next_group(self, value=0):
        # param `value` since that's what validate passes. Dunno if we need it.
        if self.reset_queue:  # there's still more to reset
            next_group = self.reset_queue.pop(0)
            self.log.debug("Resetting ScoreReelGroup %s", next_group.name)
            # add the handler to know when this group is reset
            self.machine.events.add_handler('scorereelgroup_' +
                                            next_group.name +
                                            '_valid', self._reset_next_group)
            next_group.set_value(value)

        else:  # no more to reset
            # clear the event queue
            self.queue.clear()
            self.queue = None
            # remove all these handlers watching for 0
            self.machine.events.remove_handler(self._reset_next_group)


class ScoreReelGroup(Device):
    """Represents a logical grouping of score reels in a pinball machine, where
    multiple individual ScoreReel object make up the individual digits of this
    group. This group also has support for the blank zero "inserts" that some
    machines use. This is a subclass of mpf.system.device.Device.
    """
    config_section = 'score_reel_groups'
    collection = 'score_reel_groups'
    class_label = 'score_reel_group'

    @classmethod
    def device_class_init(cls, machine):
        # If we have at least one score reel group, we need a
        # ScoreReelController
        machine.score_reel_controller = ScoreReelController(machine)

    def __init__(self, machine, name, config, collection=None, validate=True):
        super(ScoreReelGroup, self).__init__(machine, name, config, collection,
                                             validate=validate)

        self.wait_for_valid_queue = None
        self.valid = True  # Confirmed reels are showing the right values
        self.lit = False  # This group has its lights on
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

        self.reset_pulses_per_round = 5
        # Interger value of how many "pulses" should be done per reset round.
        # This is used to simulate the actual mechnical resets the way a classic
        # EM machine would do it. If you watch an EM game reset, you'll notice
        # they pulse the reels in groups, like click-click-click-click-click..
        # pause.. click-click-click-click-click.. pause.. etc. Once each reel
        # gets to zero, it stops advancing.

        # If you don't want to emulate this behavior, set this to 0. The default
        # is 5.

        # TODO / NOTE: This feature is not yet implemented.

        self.advance_queue = deque()
        # Holds a list of the next reels that for step advances.

        self.jump_in_progress = False
        # Boolean attribute that is True when a jump advance is in progress.

        # convert self.config['reels'] from strings to objects
        for reel in self.config['reels']:
            # find the object

            if reel:
                reel = self.machine.score_reels[reel]
            self.reels.append(reel)

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

        self.machine.events.add_handler('timer_tick', self.tick)

        # Need to hook this in case reels aren't done when ball ends
        self.machine.events.add_handler('ball_ending', self._ball_ending, 900)

    # ----- temp method for chime ------------------------------------
    def chime(self, chime):
        self.machine.coils[chime].pulse()

    # ---- temp chimes code end --------------------------------------

    @property
    def assumed_value_list(self):
        # List that holds the values of the reels in the group
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
        # Integer representation of the value we assume is shown on this
        # ScoreReelGroup. A value of -999 means the value is unknown.

        return self.reel_list_to_int(self.assumed_value_list)

    def initialize(self):
        """Initialized the score reels by reading their current physical values
        and setting each reel's rollover reel. This is a separate method since
        it can't run int __iniit__() because all the other reels have to be
        setup first.
        """
        self.get_physical_value_list()
        self.set_rollover_reels()

    def set_rollover_reels(self):
        """Calls each reel's `_set_rollover_reel` method and passes it a
        pointer to the next higher up reel. This is how we know whether we're
        able to advance the next higher up reel when a particular reel rolls
        over during a step advance.
        """
        for reel in range(len(self.reels)):
            if self.reels[reel] and (reel < len(self.reels) - 1):
                self.reels[reel]._set_rollover_reel(self.reels[reel + 1])

    def tick(self):
        """Automatically called once per machine tick and checks to see if there
        are any jumps or advances in progress, and, if so, calls those methods.
        """
        if self.jump_in_progress:
            self._jump_advance_step()
        elif self.advance_queue:
            self._step_advance_step()
        elif not self.valid:
            self.validate()

    def is_desired_valid(self, notify_event=False):
        """Tests to see whether the machine thinks the ScoreReelGroup is
        currently showing the desired value. In other words, is the
        ScoreReelGroup "done" moving?

        Note this ignores placeholder non-controllable digits.

        Returns: True or False
        """
        for i in range(len(self.reels)):
            if self.reels[i]:
                if self.assumed_value_list[i] != self.desired_value_list[i]:
                    if notify_event:
                        self.machine.events.post('scorereel_' +
                                                 self.reels[i].name +
                                                 '_resync')
                    return False
        return True

    def get_physical_value_list(self):
        """Queries all the reels in the group and builds a list of their actual
        current physical state, with either the value of the current switch
        or -999 if no switch is active.

        This method also updates each reel's physical value.

        Returns: List of physical reel values.
        """
        output_list = []
        for reel in self.reels:
            if reel:
                output_list.append(reel.check_hw_switches())

        return output_list

    def validate(self, value=None):
        """Called to validate that this score reel group is in the position
        the machine wants it to be in.

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

        self.log.debug("Checking to see if score reels are valid.")

        # Can't validate until the reels are done moving. This shouldn't happen
        # but we look for it just in case.
        if self.jump_in_progress or self.advance_queue:
            return False

        # If any reels are set to lazy or strict confirm, we're only going to
        # validate if they've hw_confirmed
        for reel in self.reels:

            if (reel and
                    (reel.config['confirm'] == 'lazy' or
                             reel.config['confirm'] == 'strict') and
                    not reel.hw_sync):
                return False  # need hw_sync to proceed

        self.log.debug("Desired list: %s", self.desired_value_list)
        self.log.debug("Assumed list: %s", self.assumed_value_list)
        self.log.debug("Assumed integer: %s", self.assumed_value_int)

        try:
            self.log.debug("Player's Score: %s",
                           self.machine.game.player.score)
        except:
            pass

        # todo if confirm is set to none, should we at least wait until the
        # coils are not energized to validate?

        if not self.is_desired_valid(notify_event=True):
            # FYI each reel will hw check during hw_sync, so if there's a
            # misfire that we can know about then it will be caught here
            self.machine.events.post('scorereelgroup_' + self.name + '_resync')
            self.set_value(value_list=self.desired_value_list)
            return False

        self.valid = True
        self.machine.events.post('scorereelgroup_' + self.name + '_valid',
                                 value=self.assumed_value_int)

        if self.wait_for_valid_queue:
            self.log.debug("Found a wait queue. Clearing now.")
            self.wait_for_valid_queue.clear()
            self.wait_for_valid_queue = None

        return True

    def add_value(self, value, jump=False, target=None):
        """Adds value to a ScoreReelGroup.

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
        """Resets the score reel group to display the value passed.

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
        current_time = time.time()  # local reference for speed
        # loop through the reels one by one
        for i in range(len(self.reels)):
            this_reel = self.reels[i]  # local reference for speed
            if this_reel:

                # While we're in here let's get a count of the total number
                # of reels that are energized
                if (this_reel.config['coil_inc'].
                            time_when_done > current_time):
                    num_energized += 1

                # Does this reel want to be advanced, and is it ready?
                if (self.desired_value_list[i] !=
                        self.assumed_value_list[i] and
                        this_reel.ready):

                    # Do we need (and have) hw_sync to advance this reel?

                    if (self.assumed_value_list[i] == -999 or
                                this_reel.config['confirm'] == 'strict'):

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
            reels_needing_advance[i].advance(direction=1)

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

        for position in range(len(value_list)):
            if value_list[position]:
                for num in range(value_list[position]):
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
        if reel.advance(direction=1):
            self.log.debug("Reel '%s' accepted advance", reel.name)
            self.log.debug("Reels (assumed): %s", self.assumed_value_int)
            try:
                self.log.debug("Score: %s",
                               self.machine.game.player.score)
            except:
                pass
            self.machine.events.post('reel_' + reel.name + "_advance")
            # todo should this advance event be posted here? Or by the reel?

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

        else:  # the reel did not accept the advance. Put it back in the queue
            self.advance_queue.appendleft(reel)
            self.log.debug("Reel '%s' rejected advance. We'll try again.",
                           reel.name)

    def int_to_reel_list(self, value):
        """Converts an integer to a list of integers that represent each
        positional digit in this ScoreReelGroup.

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
        value = str(value)

        # pad the string with leading zeros
        value = value.zfill(len(self.reels))

        # slice off excess characters if the value is longer than num of reels

        # how many digits do we have to slice?
        trim = len(value) - len(self.reels)
        # and... slice!
        value = value[trim:]

        # todo if we don't do the above trim then it will just show the highest
        # digits, effective "shifting" the score by one. Might be a fun feature?

        # generate our list with one digit per item
        for digit in value:
            output_list.append(int(digit))

        # reverse the list so the least significant is first
        output_list.reverse()

        # replace fake position digits with `None`
        for i in range(len(output_list)):
            if not self.reels[i]:
                output_list[i] = None

        return output_list

    def reel_list_to_int(self, reel_list):
        """Converts an list of integers to a single integer.

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
            value: The list containing the values for each score reel
                position.

        Returns:
            The resultant integer based on the list passed.
        """
        # reverse the list so it's in normal order
        reel_list.reverse()
        output = ""

        for item in reel_list:
            if type(item) is int:
                if item == -999:  # if any reels are unknown, then our int
                    return -999  # is unkown too.
                else:
                    output += str(item)
            elif type(item) is str and item.isdigit():
                # Just in case we have an number that's a string
                output += str(int(item))  # ensure no leading zeros
            else:
                output += "0"
        return int(output)

    def light(self, relight_on_valid=False, **kwargs):
        """Lights up this ScoreReelGroup based on the 'light_tag' in its
        config.
        """
        self.log.debug("Turning on Lights")
        for light in self.machine.lights.items_tagged(
                self.config['lights_tag']):
            light.on()

        self.lit = True

        # Watch for these reels going out of sync so we can turn off the lights
        # while they're resyncing

        self.unlight_on_resync_key = self.machine.events.add_handler(
            'scorereelgroup_' + self.name + '_resync',
            self.unlight,
            relight_on_valid=True)

        if relight_on_valid:
            self.machine.events.remove_handler_by_key(self.light_on_valid_key)

    def unlight(self, relight_on_valid=False, **kwargs):
        """Turns off the lights for this ScoreReelGroup based on the
        'light_tag' in its config.
        """
        self.log.debug("Turning off Lights")
        for light in self.machine.lights.items_tagged(
                self.config['lights_tag']):
            light.off()

        self.lit = False

        if relight_on_valid:
            self.light_on_valid_key = self.machine.events.add_handler(
                'scorereelgroup_' + self.name + '_valid',
                self.light,
                relight_on_valid=True)
        else:
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


class ScoreReel(Device):
    """Represents an individual electro-mechanical score reel in a pinball
    machine.

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

    def __init__(self, machine, name, config, collection=None, validate=True):
        super(ScoreReel, self).__init__(machine, name, config, collection,
                                        validate=validate)
        self.delay = DelayManager()

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
        self.assumed_value = self.check_hw_switches()
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

        self.misfires = dict()
        # Counts the number of "misfires" this reel has, which is when we
        # advanced a reel to a value where we expected a switch to activate but
        # didn't receive that activation as expected. This is a dictionary with
        # the key equal to the switch position and the value is a tuple with
        # the first entry being the number of misfires this attempt, and the
        # second value being the number of misfires overall.

        self._destination_index = 0
        # Holds the index of the destination the reel is trying to advance to.

        # todo add some kind of status for broken?

        self.log.debug("Configuring score reel with: %s", self.config)

        # figure out how many values we have
        # Add 1 so range is inclusive of the lower limit
        self.num_values = self.config['limit_hi'] - \
                          self.config['limit_lo'] + 1

        self.log.debug("Total reel values: %s", self.num_values)

        for value in range(self.num_values):
            self.value_switches.append(self.config.get('switch_' + str(value)))

    @property
    def pulse_ms(self, direction=1):
        """Returns an integer representing the number of milliseconds the coil
        will pulse for.

        This method is used by the jump and step advances so they know when a
        reel's coil is done firing so they can fire the next reel in the group.

        Args:
            direction (int, optional): Lets you specify which coil you want to
            get the time for. Default is 1 (up), but you can also specify -1 (
            down).

        Returns: Interger of the coil pulse time. If there is no coil for the
            direction you specify, returns 0.
        """
        if direction == 1:
            return self.config['coil_inc'].config['pulse_ms']
        elif self.config['coil_dec']:
            return self.config['coil_dec'].config['pulse_ms']
        else:
            return 0

    def logical_to_physical(self, value):
        """Converts a logical reel displayed value to what the physical switch
        value should be.

        For example, if a reel has switches for the 0 and 9 values, then an
        input of 0 will return 0 (since that's what the physical value should
        be for that logical value). In that case it will return 9 for an input
        of 9, but it will return -999 for any input value of 1 through 8 since
        there are no switches for those values.

        Note this method does not perform any physical or logical check against
        the reel's actual position, rather, it's only used to indicate what
        hardware switch value should be expected for the display value passed.

        Args:
            value (int): The value you want to check.

        Returns:
            The phsyical switch value, which is same as the input value if
            there's a switch there, or -999 if not.
        """
        if value != -999:

            if self.value_switches[value]:
                return value
            else:
                return -999

        return -999

    def _set_rollover_reel(self, reel):
        # Sets this reels' rollover_reel to the object of the next higher
        # reel
        self.log.debug("Setting rollover reel: %s", reel.name)
        self.rollover_reel = reel

    def advance(self, direction=None):
        """Performs the coil firing to advance this reel one position (up or
        down).

        This method also schedules delays to post the following events:

        `reel_<name>_pulse_done`: When the coil is done pulsing
        `reel_<name>_ready`: When the config['repeat_pulse_time'] time is up
        `reel_<name>_hw_value`: When the config['hw_confirm_time'] time is up

        Args:
            direction (int, optional): If direction is 1, advances the reel
                to the next higher position. If direction is -1, advances the
                reel down one position (if the reel has a decrement coil). If
                direction is not passed, this method will compare the reel's
                `_destination_index` to its `assumed_value` and will advance it
                in the direction it needs to go if those values do not match.

        Returns: If this method is unable to advance the reel (either because
            it's not ready, because it's at its maximum value and does not have
            rollover capabilities, or because you're trying to advance it in a
            direction but it doesn't have a coil for that direction), it will
            return `False`. If it's able to pulse the advance coil, it returns
            `True`.
        """
        self.log.debug("Received command advance Reel in direction: '%s'",
                       direction)

        if not direction:
            # A direction wasn't specified, but let's see if this reel wants
            # to be in another position and fire it if so
            if (self._destination_index != self.assumed_value and
                    self.config['rollover']):
                direction = 1
            elif (self._destination_index < self.assumed_value and
                      self.config['coil_dec']):
                direction = -1
            else:  # no direction specified and everything seems ok
                return

        self.set_destination_value(direction)
        # above line also sets self._destination_index

        if self.next_pulse_time > time.time():
            # This reel is not ready to pulse again
            # Note we don't allow this to be overridden. Figure the
            # recycle time is there for a reason and we don't want to
            # potentially break an old delicate mechanism
            self.log.debug("Received advance request but this reel is not "
                           "ready")
            return False  # since we didn't advance...in case anyone cares?

        if direction == 1:
            # Ensure we're not at the limit of a reel that can't roll over
            if not ((self.physical_value == self.config['limit_hi']) and
                        not self.config['rollover']):
                self.log.debug("Ok to advance")

                # Since we're firing, assume we're going to make it
                self.assumed_value = self._destination_index
                self.log.debug("+++Setting assumed value to: %s",
                               self.assumed_value)

                # Reset our statuses (stati?) :)
                self.ready = False
                self.hw_sync = False

                # fire the coil
                self.config['coil_inc'].pulse()

                # set delay to notify when this reel can be fired again
                self.delay.add(name='ready_to_fire',
                               ms=self.config['repeat_pulse_time'],
                               callback=self._ready_to_fire)

                self.next_pulse_time = (time.time() +
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

        # if direction is not 1 we'll assume down, but only if we have
        # the ability to decrement this reel
        elif 'coil_dec' in self.config:
            return False  # since we haven't written this yet  todo

            # todo log else error?

    def _pulse_done(self):
        # automatically called (via a delay) after the reel fires to post an
        # event that the reel's coil is done pulsing
        self.machine.events.post('reel_' + self.name + "_pulse_done")

    def _ready_to_fire(self):
        # automatically called (via a delay) after the reel fires to post an
        # event that the reel is ready to fire again
        self.ready = True
        self.machine.events.post('reel_' + self.name + "_ready")

    def check_hw_switches(self, no_event=False):
        """Checks all the value switches for this score reel.

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

        Args:
            no_event: A boolean switch that allows you to suppress the event
                posting from this call if you just want to update the values.

        Returns: The hardware value of the switch, either the position or -999.
            If the reel is not ready, it returns `False`.
        """
        # check to make sure the 'hw_confirm_time' time has passed. If not then
        # we cannot trust any value we read from the switches
        if (self.config['coil_inc'].time_last_changed +
                (self.config['hw_confirm_time'] / 1000.0) <= time.time()):
            self.log.debug("Checking hw switches to determine reel value")
            value = -999
            for i in range(len(self.value_switches)):
                if self.value_switches[i]:  # not all values have a switch
                    if self.machine.switch_controller.is_active(
                            self.value_switches[i].name):
                        value = i

            self.log.debug("+++Setting hw value to: %s", value)
            self.physical_value = value
            self.hw_sync = True
            # only change this if we know where we are or can confirm that
            # we're not in the right position
            if value != -999:
                self.assumed_value = value

            # if value is -999, but we have a switch for the assumed value,
            # then we're in the wrong position because our hw_value should be
            # at the assumed value
            elif (self.assumed_value != -999 and
                      self.value_switches[self.assumed_value]):
                self.assumed_value = -999

            if not no_event:
                self.machine.events.post('reel_' + self.name + "_hw_value",
                                         value=value)
            return value

        else:
            return False

    def set_destination_value(self, direction=1):
        """Returns the integer value of the destination this reel is moving to.

        Args:
            direction (int, optional): The direction of the reel movement this
            method should get the value for. Default is 1 which means of 'up'.
            You can pass -1 the next lower value.

        Returns: The value of the destination. If the current
            `self.assumed_value` is -999, this method will always return -999
            since it doesn't know where the reel is and therefore doesn't know
            what the destination value would be.
        """
        # We can only know if we have a destination if we know where we are
        self.log.debug("@@@ set_destination_value")
        self.log.debug("@@@ old destination_index: %s",
                       self._destination_index)
        if self.assumed_value != -999:
            if direction == 1:
                self._destination_index = self.assumed_value + 1
                if self._destination_index > (self.num_values - 1):
                    self._destination_index = 0
                if self._destination_index == 1:
                    self.rollover_reel_advanced = False
                self.log.debug("@@@ new destination_index: %s",
                               self._destination_index)
                return self._destination_index
            elif direction == -1:
                self._destination_index = self.assumed_value - 1
                if self._destination_index < 0:
                    self._destination_index = (self.num_values - 1)
                self.log.debug("@@@ new destination_index: %s",
                               self._destination_index)
                return self._destination_index
        else:
            self.log.debug("@@@ new destination_index: -999")
            self._destination_index = -999
            return -999

# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
