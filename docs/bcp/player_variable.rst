player_variable (BCP command)
=============================

This is a generic "catch all" which sends player-specific variables to the media controller
any time they change. Since the pin controller will most likely track hundreds of variables
per player (with many being internal things that the media controller doesn't care about),
it's recommended that the pin controller has a way to filter which player variables are
sent to the media controller. Also note the parameter *player_num* indicates which player
this variable is for (starting with 1 for the first player). While it's usually the case
that the *player_variable* command will be sent for the player whose turn it is, that's not
always the case. (For example, when a second player is added during the first player's ball,
the second player's default variables will be initialized at 0 and a *player_variable* event
for player 2 will be sent even though player 1 is up.

Origin
------
Pin controller

Parameters
----------

name
~~~~
Type: ``string``

This is the name of the player variable.

player_num
~~~~~~~~~~
Type: ``int``

This is the player number the variable is for (starting with 1 for the first player).

value
~~~~~
Type: Varies depending upon the variable type.

This is the new value of the player variable.

prev_value
~~~~~~~~~~
Type: Varies depending upon the variable type.

This is the previous value of the player variable.

change
~~~~~~
Type: Varies depending upon the variable type.

If the player variable just changed, this will be the amount of the change. If it's not possible
to determine a numeric change (for example, if this player variable is a string), then this
*change* value will be set to the boolean *True*.

Response
--------
None
