device (BCP command)
====================

Origin
------
Pin controller or media controller

Parameters
----------

type
~~~~
Type: ``string``

The type/class of device (ex: coil).

name
~~~~
Type: ``string``

The name of the device.

changes
~~~~~~~

Type: ``tuple`` (attribute name, old value, new value)

The change to the device state.

state
~~~~~

Type: varies (depending upon device type)

The device state.

Response
--------
None
