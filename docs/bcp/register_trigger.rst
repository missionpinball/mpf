register_trigger (BCP command)
==============================

Request from the media controller to the pin controller to register an event name as a trigger so
it will be sent via BCP to the media controller whenever the event is posted in MPF.

Origin
------
Media controller

Parameters
----------

event
~~~~~
Type: ``string``

This is the name of the trigger event to register with the pin controller.

Response
--------
None
