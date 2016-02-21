"""Contains the Player class which represents a player in a pinball game."""

import logging


class Player(object):
    """ Base class for a player. One instance of this class is created for each
    player.

    The Game class maintains a "player" attribute which always points to the
    current player. You can access this via game.player. (Or
    self.machine.game.player).

    This class is responsible for tracking per-player variables. There are
    several ways they can be used:

    player.ball = 0 (sets the player's 'ball' value to 0)
    print player.ball (prints the value of the player's 'ball' value)

    If the value of a variable is requested but that variable doesn't exist,
    that variable will automatically be created (and returned) with a value of
    0.

    Every time a player variable is changed, an MPF is posted with the name
    "player_<name>". That event will have three parameters posted along with it:

    * value (the new value)
    * prev_value (the old value before it was updated)
    * change (the change in the value)

    For the 'change' parameter, it will attempt to subtract the old value from
    the new value. If that works, it will return the result as the change. If it
    doesn't work (like if you're not storing numbers in this variable), then
    the change paramter will be True if the new value is different and False if
    the value didn't change.

    Some examples:

    player.score = 0

    Event posted:
    'player_score' with Args: value=0, change=0, prev_value=0

    player.score += 500

    Event posted:
    'player_score' with Args: value=500, change=500, prev_value=0

    player.score = 1200

    Event posted:
    'player_score' with Args: value=1200, change=700, prev_value=500

    """

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track player variable changes.
    """

    def __init__(self, machine, player_list):
        # use self.__dict__ below since __setattr__ would make these player vars
        self.__dict__['log'] = logging.getLogger("Player")
        self.__dict__['machine'] = machine
        self.__dict__['vars'] = dict()
        self.__dict__['uvars'] = dict()  # for "untracked" player vars

        player_list.append(self)

        index = len(player_list) - 1
        number = len(player_list)

        self.log.debug("Creating new player: Player %s. (player index '%s')", number, index)

        # Set these after the player_add_success event so any player monitors
        # get notification of the new player before they start seeing variable
        # changes for it.
        self.vars['index'] = index
        self.vars['number'] = number

        self.machine.events.post('player_add_success', player=self, num=number,
                                 callback=self._player_add_done)

    def _player_add_done(self, **kwargs):
        """ do it this way so we get the player_score event
        use a callback so this event is posted after the player add event
        """
        del kwargs
        self.score = 0

    def __repr__(self):
        try:
            return "<Player {}>".format(self.vars['number'])
        except KeyError:
            return '<Player (new)>'

    def __getattr__(self, name):
        if name in self.vars:
            return self.vars[name]
        else:
            self.vars[name] = 0
            return 0

    def __setattr__(self, name, value):
        new_entry = False
        prev_value = 0
        if name in self.vars:
            prev_value = self.vars[name]
        else:
            new_entry = True

        self.vars[name] = value

        try:
            change = value-prev_value
        except TypeError:
            if prev_value != value:
                change = True
            else:
                change = False

        if change or new_entry:

            self.log.debug("Setting '%s' to: %s, (prior: %s, change: %s)",
                           name, self.vars[name], prev_value, change)
            self.machine.events.post('player_' + name,
                                     value=self.vars[name],
                                     prev_value=prev_value,
                                     change=change,
                                     player_num=self.vars['number'])

        if Player.monitor_enabled:
            for callback in self.machine.monitors['player']:
                callback(name=name, value=self.vars[name],
                         prev_value=prev_value, change=change,
                         player_num=self.vars['number'])

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __setitem__(self, name, value):
        self.__setattr__(name, value)

    def __iter__(self):
        for name, value in self.vars.items():
            yield name, value

    def is_player_var(self, var_name):
        if var_name in self.vars:
            return True
        else:
            return False

    # todo method to dump the player vars to disk?
