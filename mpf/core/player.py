"""Contains the Player class which represents a player in a pinball game."""

import logging


class Player(object):

    """Base class for a player. One instance of this class is created for each player.

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
        """Initialise player."""
        # use self.__dict__ below since __setattr__ would make these player vars
        self.__dict__['log'] = logging.getLogger("Player")
        self.__dict__['machine'] = machine
        self.__dict__['vars'] = dict()

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
        '''event: player_add_success

        desc: A new player was just added to this game

        args:

        player: A reference to the instance of the Player() object.

        num: The number of the player that was just added. (e.g. Player 1 will
        have *num=1*, Player 4 will have *num=4*, etc.)

        '''

    def _player_add_done(self, **kwargs):
        """Set score to 0 for new player.

        Do it this way so we get the player_score event use a callback so this event is posted after the player add
        event.
        """
        del kwargs
        self.__setattr__("score", 0)

    def __repr__(self):
        """Return string representation."""
        try:
            return "<Player {}>".format(self.vars['number'])
        except KeyError:
            return '<Player (new)>'

    def __getattr__(self, name):
        """Return value of attribute or initialise it with 0 when it does not exist."""
        if name in self.vars:
            return self.vars[name]
        else:
            self.vars[name] = 0
            return 0

    def __setattr__(self, name, value):
        """Set value and post event to inform about the change."""
        new_entry = False
        prev_value = 0
        if name in self.vars:
            prev_value = self.vars[name]
        else:
            new_entry = True

        self.vars[name] = value

        try:
            change = value - prev_value
        except TypeError:
            change = prev_value != value

        if (change or new_entry) and isinstance(value, (int, str, float)):

            self.log.debug("Setting '%s' to: %s, (prior: %s, change: %s)",
                           name, self.vars[name], prev_value, change)
            self.machine.events.post('player_' + name,
                                     value=self.vars[name],
                                     prev_value=prev_value,
                                     change=change,
                                     player_num=self.vars['number'])
            '''event: player_(var_name)

            desc: Posted when simpler types of player variables are added or
            change value.

            The actual event has (var_name) replaced with the name of the
            player variable that changed. Some examples:

            * player_score
            * player_shot_upper_lit_hit

            Lots of things are stored in player variables, so there's no way to
            build a complete list of what all the options are here. Elsewhere
            in the documentation, if you see something that says it's stored in
            a player variable, that means you'll get this event when that
            player variable is created or is changed.

            Note that this event is only posted for simpler types of player
            variables, including player variables that are integers, floating
            point numbers, or strings. More complex player variables (lists,
            dicts, etc.) do not get this event posted.

            This event is posted for a single player variable changing, meaning
            if multiple player variables change at the same time, multiple
            events will be posted, one for each change.

            args:

            value: The new value of this player variable.

            prev_value: The previous value of this player variable, e.g. what
            it was before the current value.

            change: If the player variable just changed, this will be the
            amount of the change. If it's not possible to determine a numeric
            change (for example, if this player variable is a string), then
            this *change* value will be set to the boolean *True*.

            player_num: The player number this variable just changed for,
            starting with 1. (e.g. Player 1 will have *player_num=1*, Player 4
            will have *player_num=4*, etc.)

            '''

            # note the monitor is only called for simpler var changes
            if Player.monitor_enabled and "player" in self.machine.monitors:
                for callback in self.machine.monitors['player']:
                    callback(name=name, value=self.vars[name],
                             prev_value=prev_value, change=change,
                             player_num=self.vars['number'])

    def __getitem__(self, name):
        """Allow array get access."""
        return self.__getattr__(name)

    def __setitem__(self, name, value):
        """Allow array set access."""
        self.__setattr__(name, value)

    def __iter__(self):
        """Iterate all player vars."""
        for name, value in self.vars.items():
            yield name, value

    def is_player_var(self, var_name):
        """Check if player var exists."""
        return var_name in self.vars
