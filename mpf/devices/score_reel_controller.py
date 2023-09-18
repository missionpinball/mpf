"""Score reel controller."""
import logging

import asyncio
from functools import partial


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
        """initialize score reel controller."""
        self.machine = machine
        self.log = logging.getLogger("ScoreReelController")
        self.log.debug("Loading the ScoreReelController")

        self.active_scorereelgroup = None
        """Pointer to the active ScoreReelGroup for the current player.
        """
        self.player_to_scorereel_map = {}
        """This is a dict of ScoreReelGroup objects which corresponds to player
        number. The first element [1] in this dict is the first player (which
        is player number [1], the next one is the next player, etc.
        """

        self.active_reel_player_map = {}
        """This dict maps reels to players. Every reel can only have one active player but multiple players can
        share a reel.
        """
        # switch the active score reel group and reset it (if needed)
        self.machine.events.add_handler('player_turn_started',
                                        self._rotate_player)

        # receive notification of score changes
        self.machine.events.add_handler('player_score', self._score_change)

        # receives notifications of game starts to reset the reels
        self.machine.events.add_handler('game_starting', self._game_starting)

        # receives notifications of game ends to reset the reels
        self.machine.events.add_handler('game_ending', self._game_ending)

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
        # unlight active score reel group
        if self.active_scorereelgroup:
            self.active_scorereelgroup.unlight()

        self.active_scorereelgroup = self.player_to_scorereel_map[self.machine.game.player.number]

        self.active_reel_player_map[self.active_scorereelgroup] = self.machine.game.player.number

        self.log.debug("Mapping Player %s to ScoreReelGroup '%s'",
                       self.machine.game.player.number,
                       self.active_scorereelgroup.name)

        # Make sure this score reel group is showing the right score
        self.log.debug("Current player's score: %s",
                       self.machine.game.player.score)
        self.active_scorereelgroup.set_value(self.machine.game.player.score)

        self.active_scorereelgroup.light()

    def _score_change(self, value, change, player_num, **kwargs):
        """Handle score changes and add the score increase to the current active ScoreReelGroup.

        This method is the handler for the score change event, so it's called
        automatically.

        Args:
        ----
            value: Integer value of the new score. This parameter is ignored,
                and included only because the score change event passes it.
            change: Change compared to the previous score-
            player_num: Player number of the player who's score changed.
        """
        del kwargs
        del change
        # get score reel group for player
        score_reel_group = self.player_to_scorereel_map[player_num]

        # check if it is currently dedicated to that player
        if score_reel_group and self.active_reel_player_map[score_reel_group] == player_num:
            # set value
            score_reel_group.set_value(value=value)

    def _game_starting(self, queue, **kwargs):
        """Reset the score reels when a new game starts.

        This is a queue event so it doesn't allow the game start to continue
        until it's done.

        Args:
        ----
            queue: A reference to the queue object for the game starting event.
        """
        del kwargs
        # tell the game_starting event queue that we have stuff to do
        queue.wait()

        # calculate a player <-> reel mapping
        for player_num in range(1, self.machine.game.max_players + 1):
            reel = self.machine.score_reel_groups.items_tagged("player{}".format(player_num))
            if reel:
                self.player_to_scorereel_map[player_num] = reel[0]
                if reel[0] not in self.active_reel_player_map:
                    self.active_reel_player_map[reel[0]] = player_num
            else:
                self.log.warning('Did not find a score reel for player %s. Did you tag a reel with "player%s"? '
                                 'Will reuse player1',
                                 player_num, player_num)
                reel1 = self.machine.score_reel_groups.items_tagged("player1")
                self.player_to_scorereel_map[player_num] = reel1[0]
                if not reel1:
                    raise AssertionError('Need a score reel group tagged "player1"')

        futures = []
        for score_reel_group in self.machine.score_reel_groups.values():
            score_reel_group.set_value(0)
            futures.append(score_reel_group.wait_for_ready())

        future = asyncio.wait(iter(futures))
        future = asyncio.ensure_future(future)
        future.add_done_callback(partial(self._reels_ready, queue=queue))

    @staticmethod
    def _reels_ready(future, queue):
        """Unblock queue since all reels are ready."""
        del future
        queue.clear()

    def _game_ending(self, **kwargs):
        """Reset controller."""
        del kwargs
        if self.active_scorereelgroup:
            self.active_scorereelgroup.unlight()
        self.active_scorereelgroup = None
        self.player_to_scorereel_map = {}

    def _ball_ending(self, queue=None, **kwargs):
        del kwargs
        # We need to hook the ball_ending event in case the ball ends while the
        # score reel is still catching up.
        queue.wait()

        future = asyncio.ensure_future(self.active_scorereelgroup.wait_for_ready())
        future.add_done_callback(partial(self._reels_ready, queue=queue))
