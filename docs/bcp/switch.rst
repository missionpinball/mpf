switch (BCP command)
====================

Indicates that the other side should process the changed state of a switch. When sent from the
media controller to the pin controller, this is typically used to implement a virtual keyboard
interface via the media controller (where the player can activate pinball machine switches via
keyboard keys for testing). For example, for the media controller to tell the pin controller that
the player just pushed the start button, the command would be:

::

   switch?name=start&state=1

followed very quickly by

::

   switch?name=start&state=0

When sent from the pin controller to the media controller, this is used to send switch inputs to
things like video modes, high score name entry, and service menu navigation. Note that the pin
controller should not send the state of every switch change at all times, as the media controller
doesn't need it and that would add lots of unnecessary commands. Instead the pin controller
should only send switches based on some mode of operation that needs them. (For example, when the
video mode starts, the pin controller would start sending the switch states of the flipper
buttons, and when the video mode ends, it would stop.)

Origin
------
Pin controller or media controller

Parameters
----------

name
~~~~
Type: ``string``

This is the name of the switch.

state
~~~~~

Type: ``int``

The new switch state: `1` for active, and `0` for inactive.

Response
--------
None
