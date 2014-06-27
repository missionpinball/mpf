# player.py
import logging


class Player(object):

    total_players = 0  # might not use this here

    def __init__(self):
        """ Creates a new player object """
        self.log = logging.getLogger("Player")
        self.vars = {}  # todo default dic?
        self.index = Player.total_players  # player index starting with 0

        Player.total_players += 1

        # initialize player vars
        self.vars['ball'] = 0
        self.vars['score'] = 0
        self.vars['index'] = 0  # the player index (starts with 0)
        self.vars['number'] = Player.total_players

        self.log.info("Creating new player: Player %s. (player index '%s')",
                      self.vars['number'], self.index)

    # todo method to dump the player vars to disk?

