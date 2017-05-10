trigger (BCP command)
=====================

This command allows the one side to trigger the other side to do something. For example, the pin
controller might send trigger commands to tell the media controller to start shows, play sound
effects, or update the display. The media controller might send a trigger to the pin controller to
flash the strobes at the down beat of a music track or to pulse the knocker in concert with a
replay show.

Origin
------
Pin controller or media controller

Parameters
----------

name
~~~~

Type: ``string``

This is the name of the trigger.

.. note::
   Trigger messages may contain any additional parameters as needed by the application.

Response
--------
Varies
