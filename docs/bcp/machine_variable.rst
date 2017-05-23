machine_variable (BCP command)
==============================

This is a generic "catch all" which sends machine variables to the media controller any time they
change. Machine variables are like player variables, except they're maintained machine-wide
instead of per-player or per-game. Since the pin controller will most likely track hundreds of
variables (with many being internal things that the media controller doesn't care about), it'
s recommended that the pin controller has a way to filter which machine variables are
sent to the media controller.

Origin
------
Pin controller

Parameters
----------

name
~~~~
Type: ``string``

This is the name of the machine variable.

value
~~~~~
Type: Varies depending upon the variable type.

This is the new value of the machine variable.

prev_value
~~~~~~~~~~
Type: Varies depending upon the variable type.

This is the previous value of the machine variable.

change
~~~~~~
Type: Varies depending upon the variable type.

If the machine variable just changed, this will be the amount of the change. If it's not possible
to determine a numeric change (for example, if this machine variable is a string), then this
*change* value will be set to the boolean *True*.

Response
--------
None
