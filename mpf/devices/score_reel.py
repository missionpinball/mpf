""" Contains the base classes for mechanical EM-style score reels."""
# score_reel.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import time
from collections import deque
from mpf.system.devices import Device
from mpf.system.tasks import DelayManager
from mpf.system.timing import Timing

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

        self.score_reel_groups = []
        """List of score reel groups, in order."""
        # todo do we need that? I think no?
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

    def rotate_player(self):
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
                self.machine.game.player_list):
            # do we have a reel group tagged for this player?
            for reel_group in self.machine.score_reel_groups.items_tagged(
                    "player" + str(self.machine.game.player.vars['number'])):
                if reel_group:
                    self.player_to_scorereel_map.append(reel_group)
                    break

        # if we didn't find one..
        if (len(self.player_to_scorereel_map) <
                len(self.machine.game.player_list)):
            # todo: time to double up
            pass
        else:  # we found one
            self.active_scorereelgroup = self.player_to_scorereel_map[
                self.machine.game.player.vars['index']]
            self.log.debug("Mapping Player %s to ScoreReelGroup '%s'",
                           self.machine.game.player.vars['number'],
                           self.active_scorereelgroup.name)

        # todo make sure this reel is showing the player's score. If not, make
        # it so
        self.log.debug("Current player's score: %s",
                       self.machine.game.player.vars['score'])
        self.log.debug("Score displayed on reels: %s",
                       self.active_scorereelgroup.assumed_value_int)
        if (self.active_scorereelgroup.assumed_value_int !=
                self.machine.game.player.vars['score']):
            self.active_scorereelgroup.set_value(
                self.machine.game.player.vars['score'])

    def score_change(self, score, change):
        """Called whenever the score changes and adds the score increase to the
        current active ScoreReelGroup.

        This method is the handler for the score change event, so it's called
        automatically.
        """
        self.active_scorereelgroup.add_value(change)

    def game_starting(self, queue, game):
        """Resets the score reels when a new game starts.

        This is a queue event so it doesn't allow the game start to continue
        until it's done.

        Args:
            queue (event queue): A reference to the queue object for the game
                starting event.
            game (game object): A reference to the main game object.
        """

        self.queue = queue
        # tell the game_starting event queue that we have stuff to do
        self.queue.wait()

        # populate the reset queue
        self.reset_queue = []
        for score_reel_group in self.machine.score_reel_groups:
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
            next_group.set_value(0)

        else:  # no more to reset
            # clear the event queue
            self.queue.clear()
            self.queue = None
            # remove all these handlers watching for 0
            self.machine.events.remove_handler(self._reset_next_group)


class ScoreReelGroup(Device):
    """Represents a logical grouping of score reels in a pinball machine.

    These groups represent things like player scores, where the score display
    is actually a group of several individual score reels.

    """

    config_section = 'Score Reel Groups'
    collection = 'score_reel_groups'

    @classmethod
    def device_class_init(cls, machine):
        # If we have at least one score reel group, we need a
        # ScoreReelController
        machine.score_reel_controller = ScoreReelController(machine)

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('ScoreReelGroup.' + name)
        super(ScoreReelGroup, self).__init__(machine, name, config, collection)

        self.reels = []
        """A list of individual ScoreReel objects that make up this
        ScoreReelGroup. The number of items in the list correspondis to the
        number of digits that can be displayed. A value of `None` indicates a
        position that is not controlled by a moving reel (like a fake ones
        digit).

        Note that this is "backwards," with element 0 representing the ones
        digit, element 1 representing the tens, etc..
        """

        self.desired_value_list = []
        """A list of what values the machine desires to have the score reel
        group set to.
        """

        self.reset_pulses_per_round = 5
        """Interger value of how many "pulses" should be done per reset round.
        This is used to simulate the actual mechnical resets the way a classic
        EM machine would do it. If you watch an EM game reset, you'll notice
        they pulse the reels in groups, like click-click-click-click-click..
        pause.. click-click-click-click-click.. pause.. etc. Once each reel
        gets to zero, it stops advancing.

        If you don't want to emulate this behavior, set this to 0. The default
        is 5.

        TODO / NOTE: This feature is not yet implemented.
        """

        self.advance_queue = deque()
        """Holds a list of the next reels that for step advances.
        """

        self.jump_in_progess = False
        """Boolean attribute that is True when a jump advance is in progress.
        """

        self.config['reels'] = self.machine.string_to_list(
            self.config['reels'])

        if 'max simultaneous coils' not in self.config:
            self.config['max simultaneous coils'] = 2

        if 'confirm' not in self.config:
            self.config['confirm'] = 'lazy'

        # convert self.config['reels'] from strings to objects
        for reel in self.config['reels']:
            # find the object
            if reel == 'None':
                reel = None
            else:
                reel = self.machine.score_reels[reel]
            self.reels.append(reel)

        self.reels.reverse()  # We want our smallest digit in the 0th element

        # ---- temp chimes code. todo move this --------------------
        if self.config['chimes']:

            self.config['chimes'] = self.machine.string_to_list(
                self.config['chimes'])

            self.config['chimes'].reverse()

            for i in range(len(self.config['chimes'])):
                if self.config['chimes'][i] != 'None':
                    self.machine.events.add_handler(event='reel_' +
                        self.reels[i].name + '_advance', handler=self.chime,
                        chime=self.config['chimes'][i])
        # ---- temp chimes code end --------------------------------

        # register for events
        self.machine.events.add_handler('machine_init_phase1',
                                        self.set_rollover_reels)

        for reel in self.reels:
            if reel:
                self.machine.events.add_handler('reel_' + reel.name + '_ready',
                                                self._reel_state_change)
                self.machine.events.add_handler('reel_' + reel.name + '_hw_value',
                                                self._reel_state_change)
                self.machine.events.add_handler('reel_' + reel.name + '_pulse_done',
                                                self._reel_state_change)

    # ----- temp method for chime ------------------------------------
    def chime(self, chime):
        self.machine.coils[chime].pulse()
    # ---- temp chimes code end --------------------------------------

    @property
    def assumed_value_list(self):
        """ TODO add documentation"""
        # create a list that holds the values of the reels in the group
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
        """An integer representation of the value we assume is shown on this
        ScoreReelGroup. A value of -999 means the value is unknown.
        """
        return self.reel_list_to_int(self.assumed_value_list)

    def set_rollover_reels(self):
        """Calls each reel's `_set_rollover_reel` method and passes it a
        pointer to the next higher up reel. This is how we know whether we're
        able to advance the next higher up reel when a particular reel rolls
        over during a step advance.
        """
        for reel in range(len(self.reels)):
            if self.reels[reel] and (reel < len(self.reels) - 1):
                self.reels[reel]._set_rollover_reel(self.reels[reel+1])

    def is_desired_valid(self):
        """Tests to see whether the machine thinks the ScoreReelGroup is
        currently showing the desired value. In other words, is the
        ScoreReelGroup "done" moving?

        Note this ignores placeholder non-controllable digits.

        Returns: True or False
        """
        self.log.debug("+++ is_desired_valid. a: %s d: %s",
                       self.assumed_value_list,
                       self.desired_value_list)
        for i in range(len(self.reels)):
            if i:
                if self.assumed_value_list[i] != self.desired_value_list[i]:
                    return False
        return True

    def get_physical_value_list(self):
        """Queries all the reels in the group and builds a list of their actual
        current physical state, with either the value of the current switch
        or -999 if no switch is active.

        This method also updates each reel's physical value

        Returns: List of physical reel values.
        """
        # todo this method is not used.. keep it?
        output_list = []
        for reel in self.reels:
            if reel:
                output_list.append(reel.get_physical_value())

        return output_list

    def validate(self, value=None):
        """Called to validate that this score reel group is in the position
        the machine wants it to be in.

        If lazy confirm mode is enabled, this method will also make sure the
        reels are in their proper physical positions. If any reels are not done
        moving, it will add event handlers to receive notifications of when the
        reels are done and will call this method again at that time.

        Args:
            value (ignored): This method takes an argument of `value`, but
                it's not used. It's only there because when reels post their
                events after they're done moving, they include a parameter of
                `value` which is the position they're in. So we just need to
                have this argument listed so we can use this method as an event
                handler for those events.
        """
        self.log.debug("Checking to see if score reels are valid.")
        self.log.debug("Assumed list: %s", self.assumed_value_list)
        self.log.debug("Desired list: %s", self.desired_value_list)
        self.log.debug("advance_queue: %s", self.advance_queue)
        self.log.debug("jump_in_progess: %s", self.jump_in_progess)

        if self.advance_queue or self.jump_in_progess:
            # We got here but something is still moving the reels
            return False

        # If any reels are set to lazy confirm, we're only going to validate
        # this jump if they've hw_confirmed
        for reel in self.reels:
            if reel and reel.config['confirm'] == 'lazy' and not reel.hw_sync:
                self.jump_in_progess = True
                # causes the reel's hw_confirm to return back to the jump
                # advance which will ultimately lead back here
                return False

        self.machine.events.post('scorereelgroup_' + self.name + '_valid',
                                 value=self.assumed_value_int)

    def add_value(self, value, jump=False):
        """Add value to a ScoreReelGroup.

        You can also pass a negative value to subtract points.

        Note you can control the logistics of how these pulses are applied via
        the `jump` parameter. If jump is False (the default), then this method
        whill respect the proper "sequencing" of reel advances. For example,
        if the current value is 1700 and the new value is 2200, this method
        will fire the hundreds reel twice (to go to 1800 then 1900), then on
        the third pulse it will fire the thousands and hundreds (to go to
        2000), then do the final two pulses to land at 2200.

        Args:
            value (int): The integer value you'd like to add to (or subtract
                from) the current value

            jump (bool, optional): Whether the reels should "count up" to the
                new value in the classic EM way (jump=False) or whether they
                should just jump there as fast as they can (jump=True). Default
                is False.
        """

        self.log.debug("Adding '%s' to the displayed value. Jump=%s", value,
                       jump)
        self.log.debug("Current assumed value: %s", self.assumed_value_list)

        if self.assumed_value_int == - 999:
            self.log.debug("Current displayed value is unkown, "
                           "so we're jumping to the new value.")
            jump = True

        elif value < 0:
            self.log.debug("add_value is negative, so we're subtracting this "
                           "value. We will do this via a jump.")
            jump = True

        if jump:
            self.set_value(self.assumed_value_int + value, jump)
        else:
            self._step_advance_add_steps(value)

    def set_value(self, value=None, value_list=None):
        """Resets the score reel group to display the value passed.

        This method will "jump" the score reel group to display the value
        that's passed as an it. (Note this "jump" technique means it will just
        move the reels as fast as it can, and nonsensical values might show up
        on the reel while the movement is in place.

        This method is used to "reset" a reel group to all zeros at the
        beginning of a game, and can also be used to reset a reel group that is
        confused or to switch a reel to the new player's score if multiple
        players a sharing the same reel.

        Note you can choose to pass either an integer representation of the
        value, or a value list.

        Args:
            value (int, optional): An integer value of what the new displayed
                value (i.e. score) should be. This is the default option if you
                only pass a single positional argument, e.g. `set_value(2100)`.

            value_list (list, optional): A value_list of the value you'd like
            the reel group to display.
        """

        self.log.debug("Jumping to set displayed value to '%s'.", value)

        if not value_list:
            self.desired_value_list = self.int_to_reel_list(value)
        self.log.debug("desired_value_list: %s", self.desired_value_list)
        self.log.debug("assumed_value_list: %s", self.assumed_value_list)

        # Check to see if the reels are currently showing the desired values
        if not self.is_desired_valid():
            self._jump_advance_step()
        else:
            self._jump_advance_complete()

    def _jump_advance_step(self, value=None):
        # Checks the assumed values of the reels in the group, and if they're
        # off will automatically correct them.

        # This method is automatically called after any member reel changes
        # state, including that a coil is done firing, it's ready to advance,
        # or it just got hw_sync.

        # Before we do anything, we make sure we have the latest from the reels.
        # Note this will only read the switches if the 'hw_confirm_ms' time has
        # passed since they last advanced.
        for reel in self.reels:
            if reel:
                reel.check_hw_switches(no_event=True)

        self.log.debug("Entering _jump_advance_step")
        self.log.debug("Assumed values: %s", self.assumed_value_list)
        self.log.debug("Desired values: %s", self.desired_value_list)

        # if our assumed values match the desired values, we're done
        if self.is_desired_valid():
            self.log.debug("They match! We're done.")
            self._jump_advance_complete()
            return

        self.jump_in_progess = True

        reels_needing_advance = []  # reels that need to be advanced
        num_energized = 0  # count of the number of coils currently energized
        current_time = time.time()  # local reference for speed
        # loop through the reels one by one
        for i in range(len(self.reels)):
            this_reel = self.reels[i]  # local reference for speed
            if this_reel:

                self.log.debug("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                self.log.debug("~~ Reel: %s", this_reel.name)
                self.log.debug("~~ Ready: %s", this_reel.ready)
                self.log.debug("~~ d: %s", self.desired_value_list[i])
                self.log.debug("~~ a: %s", self.assumed_value_list[i])
                self.log.debug("~~ hw sync: %s", this_reel.hw_sync)

                # While we're in here let's get a count of the total number
                # of reels that are energized
                if (self.machine.coils[this_reel.config['coil_inc']].
                        time_when_done > current_time):
                    num_energized += 1

                # Does this reel want to be advanced, and is it ready?
                if (self.desired_value_list[i] != self.assumed_value_list[i]
                        and this_reel.ready):

                    # Do we need (and have) hw_sync to advance this reel?
                    if ((self.assumed_value_list[i] == -999 or
                            this_reel.config['confirm'] == 'strict') and
                            this_reel.hw_sync):
                        reels_needing_advance.append(this_reel)

                    else:  # If not we can advance on ready alone
                        if this_reel.ready:
                            reels_needing_advance.append(this_reel)

        # How many reels can we advance now?
        coils_this_round = (self.config['max simultaneous coils'] -
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

        self.jump_in_progess = False
        self.validate()

        # todo need to add lazy validation

    def _step_advance_add_steps(self, value):
        #Receives an integer value, converts it to steps, adds them to the
        #step queue, and kicks off the step advance process.
        #For example, adding a value of 210 would result the following items
        #added to the advance queue: [coil_10, coil_100, coil_100]

        value_list = self.int_to_reel_list(value)

        for position in range(len(value_list)):
            if value_list[position]:
                for num in range(value_list[position]):
                    self.advance_queue.append(self.reels[position])

        self._step_advance_step()

    def _step_advance_step(self):
        # Kicks off any advances that are in the advance_queue
        # This method is also called after a reel confirms a step advance

        # todo if reel status is bad, do something

        self.log.debug("Entering _step_advance_step to see if we can advance "
                       "any reels")

        if not self.advance_queue:
            # Looks like we're all done and confirmed
            self.validate()
            return

        # set our working reel to be the next one in the queue
        reel = self.advance_queue[0]

        # Return if this real is not ready. The reel events will pick this up
        # later
        if not reel.ready:
            return

        # finally looks like we can fire that reel

        # pop it from the queue
        reel = self.advance_queue.popleft()

        # check to see if this reel is at its limit which means we need to
        # insert an advance for the next higher reel into our queue
        if reel.assumed_value == reel.config['limit_hi']:
            # insert the rollover reel
            if reel.rollover_reel:
                self.advance_queue.appendleft(reel.rollover_reel)
            else:
                # whoops, we don't have a rollover reel. Yay for this player!
                self.machine.events.post('scorereelgroup_' + self.name + '_rollover')

        # advance the reel
        reel.advance(direction=1)

        # post the event to notify others we're advancing the reel
        self.machine.events.post('reel_' + reel.name + "_advance")

        if self.advance_queue:
            # if we have any more reels in the queue, try to advance them now
            self._step_advance_step()
        else:
            self.validate()

    def _reel_state_change(self, **kwargs):
        # A member reel has just finished something (either pulsing, advancing,
        # or hw_confirming), so let's see if we can do anything else
        if self.jump_in_progess:
            self._jump_advance_step()
        elif self.advance_queue:
            self._step_advance_step()

    def int_to_reel_list(self, value):
        """Converts an integer to a list of integers that represent each
        positional digit in this ScoreReelGroup.

        The list returned is customized for this ScoreReelGroup both in terms
        of number of elements and values of `None` used to represent blank
        plastic inserts that are not controlled by a score reel unit.

        For example, if you have a 5-digit score reel group that has 4
        phyiscial reels in the tens through ten-thousands position and a fake
        plastic "0" insert for the ones position, if you pass this method a
        value of `12300`, it will return `[None, 0, 3, 2, 1]`

        This method will also pad shorter ints with zeros, and it will chop off
        leading digits for ints that are too long. (For example, if you pass a
        value of 10000 to a ScoreReelGroup which only has 4 digits, the
        returns list would correspond to 0000, since your score reel unit has
        rolled over.)

        Args:
            value (int): The interger value you'd like to convert.

        Returns:
            A list containing the values for each corresponding score reel.

        """

        if value == -999:
            value = 0
            # todo hack

        output_list = []

        # convert our number to a string
        value = str(value)

        # pad the string with leading zeros
        value = value.zfill(len(self.reels))

        # trim off excess characters if the value is longer than num of reels
        value = value[:len(self.reels)]

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
            value (list): The list containing the values for each score reel
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
                    return -999   # is unkown too.
                else:
                    output += str(item)
            elif type(item) is str and item.isdigit():
                # Just in case we have an number that's a string
                output += str(int(item))  # ensure no leading zeros
            else:
                output += "0"
        return int(output)


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

    config_section = 'Score Reels'
    collection = 'score_reels'

    def __init__(self, machine, name, config, collection=None):
        self.log = logging.getLogger('ScoreReel.' + name)
        super(ScoreReel, self).__init__(machine, name, config, collection)
        self.delay = DelayManager()

        # set config defaults
        if 'coil_inc' not in self.config:
            self.config['coil_inc'] = None
        if 'coil_dec' not in self.config:
            self.config['coil_dec'] = None
        if 'rollover' not in self.config:
            self.config['rollover'] = True
        if 'limit_lo' not in self.config:
            self.config['limit_lo'] = 0
        if 'limit_hi' not in self.config:
            self.config['limit_hi'] = 9
        if 'repeat_pulse_ms' not in self.config:
            self.config['repeat_pulse_ms'] = '200ms'
        if 'hw_confirm_ms' not in self.config:
            self.config['hw_confirm_ms'] = '300ms'
        if 'confirm' not in self.config:
            self.config['confirm'] = 'lazy'

        # Convert times strings to ms ints
        self.config['repeat_pulse_ms'] = \
            Timing.string_to_ms(self.config['repeat_pulse_ms'])
        self.config['hw_confirm_ms'] = \
            Timing.string_to_ms(self.config['hw_confirm_ms'])

        self.value_switches = []
        """ This is a list with each element corresponding to a value on the
        reel. An entry of None means there's no value switch there. An entry
        of a reference to a switch object (todo or switch name?) means there is
        a switch there.
        """
        self.num_values = 0
        """The number of values on this wheel. This starts with zero, so a
        wheel with 10 values will have this value set to 9. (This actually
        makes sense since most (all?) score reels also have a zero value.)
        """

        self.physical_value = -999
        """The physical confirmed value of this reel. This will always
        be the value of whichever switch is active or -999. This differs from
        `self.assumed_value` in that assumed value will make assumptions about
        where the reel is as it pulses through values with no swithces, whereas
        this physical value will always be -999 if there is no switch telling
        it otherwise.

        Note this value will be initialized via self.check_hw_switches() below.
        """

        self.hw_sync = False
        """Specifies whether this reel has verified it's positions via the
        switches since it was last advanced."""

        self.ready = True
        """Whether this reel is ready to advance. Typically used to make sure
        it's not trying to re-fire a stuck position."""

        self.assumed_value = self.check_hw_switches()
        """The assumed value the machine thinks this reel is showing. A value
        of -999 indicates that the value is unknown.
        """

        self.next_pulse_time = 0
        """The time when this reel next wants to be pulsed. The reel will set
        this on its own (based on its own attribute of how fast pulses can
        happen). If the ScoreReelController is ready to pulse this reel and the
        value is in the past, it will do a pulse. A value of 0 means this reel
        does not currently need to be pulsed. """

        self.rollover_reel = None
        """A reference to the ScoreReel object of the next higher reel in the
        group. This is used so the reel can notify its neighbor that it needs
        to advance too when this reel rolls over."""

        self.misfires = dict()
        """Counts the number of "misfires" this reel has, which is when we
        advanced a reel to a value where we expected a switch to activate but
        didn't receive that activation as expected. This is a dictionary with
        the key equal to the switch position and the value is a tuple with
        the first entry being the number of misfires this attempt, and the
        second value being the number of misfires overall.
        """

        self._destination_index = 0
        """Holds the index of the destination the reel is trying to advance to.
        """

        # todo add some kind of status for broken?

        self.log.debug("Configuring score reel with: %s", self.config)

        # figure out how many values we have
        # Add 1 so range is inclusive of the lower limit
        self.num_values = self.config['limit_hi'] - \
            self.config['limit_lo'] + 1

        self.log.debug("Total reel values: %s", self.num_values)

        for value in range(self.num_values):
            self.value_switches.append(self.config.get('switch_' +
                                                          str(value)))

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
            return self.machine.coils[self.config['coil_inc']].config['pulse_ms']
        elif self.config['coil_dec']:
            return self.machine.coils[self.config['coil_dec']].config['pulse_ms']
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
        `reel_<name>_ready`: When the config['repeat_pulse_ms'] time is up
        `reel_<name>_hw_value: When the config['hw_confirm_ms'] time is up

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

                # Reset our statuses (stati?) :)
                self.ready = False
                self.hw_sync = False

                # fire the coil
                self.machine.coils[self.config['coil_inc']].pulse()

                # set delay to notify when this reel can be fired again
                self.delay.add('ready_to_fire',
                               self.config['repeat_pulse_ms'],
                               self._ready_to_fire)

                self.next_pulse_time = (time.time() +
                                      (self.config['repeat_pulse_ms'] /
                                      1000.0))
                self.log.debug("@@@ New Next pulse ready time: %s",
                               self.next_pulse_time)

                # set delay to check the hw switches
                self.delay.add('hw_switch_check',
                               self.config['hw_confirm_ms'],
                               self.check_hw_switches)

                return True

            else:
                self.log.warning("Received command to increment reel, but "
                                 "we're at the max limit and this reel "
                                 "cannot roll over")
                return False

        # if direction is not 1 we'll assume down, but only if we have
        # the ability to decrement this reel
        elif 'coil_dec' in self.config:
            pass  # copy the inc from above todo

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
        `self.config['hw_confirm_ms']`.

        TODO: What happens if there are multiple active switches? Currently it
        will return the highest one. Is that ok?

        Args:
            no_event: A boolean switch that allows you to suppress the event
                posting from this call if you just want to update the values.

        Returns: The hardware value of the switch, either the position or -999.
            If the reel is not ready, it returns `False`.
        """
        # check to make sure the 'hw_confirm_ms' time has passed. If not then we
        # cannot trust any value we read from the switches
        if (self.machine.coils[self.config['coil_inc']].time_last_changed +
                (self.config['hw_confirm_ms'] / 1000.0) <= time.time()):
            self.log.debug("Checking hw switches to determine reel value")
            value = -999
            for i in range(len(self.value_switches)):
                if self.value_switches[i]:  # not all values have a switch
                    if self.machine.switch_controller.is_active(
                            self.value_switches[i]):
                        value = i

            self.log.debug("Setting hw value to: %s", value)
            self.physical_value = value
            self.hw_sync = True
            if value != -999:  # only change this if we know where we are
                self.assumed_value = value
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
                if self._destination_index > (self.num_values-1):
                    self._destination_index = 0
                self.log.debug("@@@ new destination_index: %s",
                               self._destination_index)
                return self._destination_index
            elif direction == -1:
                self._destination_index = self.assumed_value - 1
                if self._destination_index < 0:
                    self._destination_index = (self.num_values-1)
                self.log.debug("@@@ new destination_index: %s",
                               self._destination_index)
                return self._destination_index
        else:
            self.log.debug("@@@ new destination_index: -999")
            self._destination_index = -999
            return -999

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
