# game.py
# This is the main task that runs a game.

import logging
import mpf.tasks
import mpf.machine_mode
import mpf.player
import mpf.events


class Game(mpf.machine_mode.MachineMode):

    def __init__(self, machine):
        super(Game, self).__init__(machine)
        self.log = logging.getLogger("Game")

        # Intialize variables
        mpf.player.Player.total_players = 0
        self.player = None  # This is the current player
        self.player_list = []

        self.num_balls_in_play = 0

        # todo register for request_to_start_game so you can deny it, or allow
        # it with a long press
        self.machine.events.add_handler('ball_add_live_success',
                                        self.ball_add_live_success)
        self.machine.events.add_handler('ball_remove_live',
                                        self.ball_remove_live)
        self.machine.events.add_handler('player_add_success',
                                        self.player_add_success)
        self.machine.events.add_handler('sw_start',
                                        self.request_player_add)

    def start(self):
        super(Game, self).start()
        self.log.info("Game Starting!!")
        # todo audit game start

        self.machine.events.post('game_start', game=self)
        self.request_player_add()  # if this fails we're in limbo.

    def player_add_success(self, player):
        if player.vars['number'] == 1:  # this is the first player
            self.player_turn_start()

    def tick(self):
        while self.active:
            # do something here
            yield

    """
      _____                       __ _
     / ____|                     / _| |
    | |  __  __ _ _ __ ___   ___| |_| | _____      __
    | | |_ |/ _` | '_ ` _ \ / _ \  _| |/ _ \ \ /\ / /
    | |__| | (_| | | | | | |  __/ | | | (_) \ V  V /
     \_____|\__,_|_| |_| |_|\___|_| |_|\___/ \_/\_/

    """

    def ball_starting(self):
        self.log.debug("ball_starting for Ball %s", self.player.vars['ball'])
        self.machine.events.post('ball_starting', ev_type='queue',
                                 callback=self.ball_started)

    def ball_started(self, ev_result=True):
        if ev_result is False:
            return
            # todo what happens if this fails? I mean it shouldn't, but if
            # any ball_starting handler returns False, it will fail and we'll
            # be in limbo?
        self.log.debug("ball_started for Ball %s", self.player.vars['ball'])
        self.machine.enable_autofires()  # move to machine_controller
        self.machine.enable_flippers()

        # todo skillshot
        self.machine.events.post('ball_started')
        # todo post event to reset pf?

    def ball_ending(self):
        # todo check tilt

        # todo everything below is hard coded temporary
        self.machine.disable_autofires()
        self.machine.disable_flippers()

        self.machine.events.post('ball_ending', ev_type='queue',
                                 callback=self.ball_ended)

    def ball_ended(self, ev_result=True):
        if ev_result is False:
            return
        # todo check extra balls
        # todo next_player()
        print self.player.vars['ball']
        print self.machine.config['Game']['Balls per game']
        print self.player.vars['number']
        print mpf.player.Player.total_players

        if self.player.vars['ball'] == self.machine.config['Game']\
                ['Balls per game'] and \
                self.player.vars['number'] == mpf.player.Player.total_players:
            self.game_ending()
        else:
            self.player_rotate()
            self.player_turn_start()

    def game_ending(self):
        pass
        self.machine.events.post('game_ending', ev_type='queue',
                                 callback=self.game_end)

    def game_end(self, ev_result=True):
        if ev_result is False:
            return
        self.log.debug("game_end")
        # todo disable flippers
        # todo audit games played
        # todo audit game time
        # todo audit score
        # todo post game end event
        self.machine.events.post('machine_flow_advance')

    def shoot_again(self):
        pass

    def ball_saved(self):
        pass

    def ball_add_live_success(self):
        self.num_balls_in_play += 1

    def ball_remove_live(self):
        self.num_balls_in_play -= 1
        if not self.num_balls_in_play:
            self.ball_ending()

    """
    _____  _
   |  __ \| |
   | |__) | | __ _ _   _  ___ _ __
   |  ___/| |/ _` | | | |/ _ \ '__|
   | |    | | (_| | |_| |  __/ |
   |_|    |_|\__,_|\__, |\___|_|
                    __/ |
                   |___/
    """

    def request_player_add(self):
        """ If this is successfu, it posts event 'player_add_success' with
        the new player object as player= kwarg.
        """
        self.log.debug("Received request to add player.")

        # There area few things we have to check first. If this all passes,
        # then we'll raise the event to ask other modules if it's ok to add a
        # player

        if len(self.player_list) >= self.machine.config['Game']\
                ['Max players per game']:
            self.log.debug("Game is at max players. Cannot add another.")
            return False

        if self.player and self.player.vars['ball'] > 1:  # todo config setting
            self.log.debug("Current ball is after Ball 1. Cannot add player.")
            return False

        self.machine.events.post('player_add_request', ev_type='boolean',
                                 callback=self._player_add)

    def _player_add(self, ev_result=True):
        # This is the callback from our request player add event
        if ev_result is False:
            self.log.debug("Request to add player has been denied.")
        else:
            new_player = mpf.player.Player()
            self.player_list.append(new_player)
            self.machine.events.post('player_add_success', player=new_player)

    def player_turn_start(self):
        # Called at the beginning of a player's turn. Note this is only called
        # when a new player is first up. i.e. if they get extra balls and stuff
        # this is not called again.

        # If we get a request to start a turn but we haven't done a rotate to
        # set the first player, do that now.
        if not self.player:
            self.player_rotate()

        self.player.vars['ball'] += 1
        self.machine.events.post('player_turn_start')
        self.ball_starting()  # todo is this ok to jump right into?
        # todo wonder if we should do player_turn_start as boolean? meh..

    def player_rotate(self, player_num=None):
        # sets self.player to be the next player
        # todo can do cool stuff in the future to change order, etc.

        if not self.player:
            self.player = self.player_list[0]
        else:

            if self.player.vars['number'] < mpf.player.Player.total_players:
                self.player = self.player_list[self.player.vars['number']]
                # Note the above line is kind of confusing but it works because
                # the current player number is always 1 more than the index.
                # i.e. "Player 1" has an index of 0, etc. So using the current
                # player number as the next player's index works out.
            else:
                self.player = self.player_list[0]
        self.log.info("Player rotate: Now up is Player %s",
                      self.player.vars['number'])



# player events should come next, including tracking inc/dec, other values

# sub mode(s)?
# tilted
# bonus