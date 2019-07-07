"""Contains the Player class which represents a player in a pinball game."""
import copy
import logging

from mpf.core.utility_functions import Util


class Player:

    """Base class for a player in a game.

    One instance of this class is automatically created for each player.

    The game mode maintains a ``player`` attribute which always points to the
    current player and is available via ``self.machine.game.player``.

    It also contains a ``player_list`` attribute which is a list
    of the player instances (in order) which you can use to access the
    non-current player.

    This Player class is responsible for tracking *player variables* which
    is a dictionary of key/value pairs maintained on a per-player basis. There
    are several ways they can be used:

    First, player variables can be accessed as attributes of the player
    object directly. For example, to set a player variable `foo` for the
    current player, you could use:

    .. code::

        self.machine.player.foo = 0

    If that variable didn't exist, it will be automatically created.

    You can get the value of player variables by accessing them directly. For
    example:

    .. code::

        print(self.machine.player.foo)  # prints 0

    If you attempt to access a player variable that doesn't exist, it will
    automatically be created with a value of ``0``.

    Every time a player variable is created or changed, an MPF event is posted
    in the form *player_* plus the variable name. For example, creating or
    changing the `foo` variable will cause an event called *player_foo* to
    be posted.

    The player variable event will have four parameters posted along with it:

    * ``value`` (the new value)
    * ``prev_value`` (the old value before it was updated)
    * ``change`` (the change in the value)
    * ``player_num`` (the player number the variable belongs to)

    For the ``change`` parameter, it will attempt to subtract the old value
    from the new value. If that works, it will return the result as the change.
    If it doesn't work (like if you're not storing numbers in this variable),
    then the change parameter will be *True* if the new value is different and
    *False* if the value didn't change.

    For examples, the following three lines:

    .. code::

        self.machine.player.score = 0
        self.machine.player.score += 500
        self.machine.player.score = 1200

    ... will cause the following three events to be posted:

    ``player_score`` with Args: ``value=0, change=0, prev_value=0``
    ``player_score`` with Args: ``value=500, change=500, prev_value=0``
    ``player_score`` with Args: ``value=1200, change=700, prev_value=500``

    """

    monitor_enabled = False
    """Class attribute which specifies whether any monitors have been registered
    to track player variable changes.
    """

    def __init__(self, machine, index):
        """Initialise player."""
        # use self.__dict__ below since __setattr__ would make these player vars
        self.__dict__['log'] = logging.getLogger("Player")
        self.__dict__['machine'] = machine
        self.__dict__['vars'] = dict()
        self.__dict__['_events_enabled'] = False

        number = index + 1

        self.log.debug("Creating new player: Player %s. (player index '%s')", number, index)

        # Set these after the player_added event so any player monitors
        # get notification of the new player before they start seeing variable
        # changes for it.
        self.vars['index'] = index
        '''player_var: index

        desc: The index of this player, starting with 0. For example, Player
        1 has an index of 0, Player 2 has an index of 1, etc.

        If you want to get the player number, use the "number" player variable
        instead.
        '''

        self.vars['number'] = number
        '''player_var: number

        desc: The number of the player, beginning with 1. (e.g. Player 1 has
        a number of "1", Player 2 is "2", etc.
        '''

        self._load_initial_player_vars()

        # Set the initial player score to 0
        self.__setattr__("score", 0)
        '''player_var: score

        desc: The player's score.
        '''

    def _load_initial_player_vars(self):
        """Load initial player var values from config."""
        if 'player_vars' not in self.machine.config:
            return

        config = self.machine.config['player_vars']
        for name, element in config.items():
            element = self.machine.config_validator.validate_config("player_vars", copy.deepcopy(element))
            self[name] = Util.convert_to_type(element['initial_value'], element['value_type'])

    def enable_events(self, enable=True, send_all_variables=True):
        """Enable/disable player variable events.

        Args:
            enable: Flag to enable/disable player variable events
            send_all_variables: Flag indicating whether or not to send an event
                with the current value of every player variable.
        """
        self._events_enabled = enable   # noqa

        # Send all current player variable values as events (if requested)
        if enable and send_all_variables:
            self.send_all_variable_events()

    def send_all_variable_events(self):
        """Send a player variable event for the current value of all player variables."""
        for name, value in self.vars.items():
            if isinstance(value, (int, str, float)):
                if isinstance(value, str):
                    self._send_variable_event(name, value, value, False, self.vars['number'])
                else:
                    self._send_variable_event(name, value, value, 0, self.vars['number'])

    # pylint: disable-msg=too-many-arguments
    def _send_variable_event(self, name: str, value, prev_value, change, player_num: int):
        """Send a player variable event performs any monitor callbacks if configured.

        :param name: The player variable name
        :param value: The new variable value
        :param prev_value: The previous variable value
        :param change: The change in value or True/False
        :param player_num: The player number this variable belongs to
        """
        self.machine.events.post('player_' + name,
                                 value=value,
                                 prev_value=prev_value,
                                 change=change,
                                 player_num=player_num)
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
                callback(name=name, value=value,
                         prev_value=prev_value, change=change,
                         player_num=player_num)

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
        # prevent events for internal variables
        if name in self.__dict__:
            self.__dict__[name] = value
            return

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

            if self._events_enabled:
                self._send_variable_event(name, self.vars[name], prev_value, change, self.vars['number'])

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
        """Check if player var exists.

        Args:
            var_name: String name of the player variable to test.

        Returns: *True* if the variable exists and *False* if not.

        """
        return var_name in self.vars
