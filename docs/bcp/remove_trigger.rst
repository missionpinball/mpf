remove_trigger (BCP command)
============================

.. versionadded:: 0.33

Request from the media controller to the pin controller to cancel/deregister an event name as a
trigger so it will no longer be sent via BCP to the media controller whenever the event is posted
in MPF.

Origin
------
Media controller

Parameters
----------

event
~~~~~
Type: ``string``

This is the name of the trigger event to cancel/deregister with the pin controller.

Response
--------
None
