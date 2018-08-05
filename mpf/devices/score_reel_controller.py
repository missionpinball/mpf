"""Score reel controller."""
import logging

import asyncio
from functools import partial

from mpf.core.utility_functions import Util


class ScoreReelController:

    """The overall controller that is in charge of and manages the score reels in a pinball machine.

    The main thing this controller does is keep track of how many
    ScoreReelGroups there are in the machine and how many players there are,
    as well as maps the current player to the proper score reel.

    This controller is also responsible for working around broken
    ScoreReelGroups and "stacking" and switching out players when there are
    multiple players per ScoreReelGroup.

    Known limitations of this module:
        * Assumes all score reels include a zero value.
        * Assumes all score reels count up or down by one.
        * Assumes all score reels map their displayed value to their stored
          value in a 1:1 way. (i.e. value[0] displays 0, value[5] displays 5,
          etc.
        * Currently this module only supports "incrementing" reels (i.e.
          counting up). Decrementing support will be added in the future.
    """

    config_name = "score_reel_controller"

    def __init__(self, machine):
        """Initialise score reel controller."""
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

        # register for events

        # switch the active score reel group and reset it (if needed)
        self.machine.events.add_handler('player_turn_started',
                                        self._rotate_player)

        # receive notification of score changes
        self.machine.events.add_handler('player_score', self._score_change)

        # receives notifications of game starts to reset the reels
        self.machine.events.add_handler('game_starting', self._game_starting)

        # Need to hook this in case reels aren't done when ball ends
        self.machine.events.add_handler('ball_ending', self._ball_ending, 900)

    def _rotate_player(self, **kwargs):
        """Start a new player's turn.

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
        del kwargs

        # if our player to reel map is less than the number of players, we need
        # to create a new mapping
        if (len(self.player_to_scorereel_map) <
                len(self.machine.game.player_list)):
            self._map_new_score_reel_group()

        self.active_scorereelgroup = self.player_to_scorereel_map[
            self.machine.game.player.index]

        self.log.debug("Mapping Player %s to ScoreReelGroup '%s'",
                       self.machine.game.player.number,
                       self.active_scorereelgroup.name)

        # Make sure this score reel group is showing the right score
        self.log.debug("Current player's score: %s",
                       self.machine.game.player.score)
        self.active_scorereelgroup.set_value(self.machine.game.player.score)

        # light up this group
        for group in self.machine.score_reel_groups:
            group.unlight()

        self.active_scorereelgroup.light()

    def _map_new_score_reel_group(self):
        """Create a mapping of a player to a score reel group."""
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

    def _score_change(self, value, change, **kwargs):
        """Handle score changes and add the score increase to the current active ScoreReelGroup.

        This method is the handler for the score change event, so it's called
        automatically.

        Args:
            score: Integer value of the new score. This parameter is ignored,
                and included only because the score change event passes it.
        """
        del kwargs
        del change
        if self.active_scorereelgroup:
            self.active_scorereelgroup.set_value(value=value)

    def _game_starting(self, queue, **kwargs):
        """Reset the score reels when a new game starts.

        This is a queue event so it doesn't allow the game start to continue
        until it's done.

        Args:
            queue: A reference to the queue object for the game starting event.
        """
        del kwargs
        # tell the game_starting event queue that we have stuff to do
        queue.wait()

        futures = []
        for score_reel_group in self.machine.score_reel_groups:
            score_reel_group.set_value(0)
            futures.append(score_reel_group.wait_for_ready())

        future = asyncio.wait(iter(futures), loop=self.machine.clock.loop)
        future = Util.ensure_future(future, loop=self.machine.clock.loop)
        future.add_done_callback(partial(self._reels_ready, queue=queue))

    @staticmethod
    def _reels_ready(future, queue):
        """Unblock queue since all reels are ready."""
        del future
        queue.clear()

    def _ball_ending(self, queue=None, **kwargs):
        del kwargs
        # We need to hook the ball_ending event in case the ball ends while the
        # score reel is still catching up.

        queue.wait()

        future = Util.ensure_future(self.active_scorereelgroup.wait_for_ready(), loop=self.machine.clock.loop)
        future.add_done_callback(partial(self._reels_ready, queue=queue))
