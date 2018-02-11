hello (BCP command)
===================

This is the initial handshake command upon first connection. It sends the BCP protocol version
that the origin controller speaks.

Origin
------
Pin controller or media controller

Parameters
----------

version
~~~~~~~
Type: ``string``

The BCP communication specification version implemented in the controller (ex: 1.0).

controller_name
~~~~~~~~~~~~~~~

Type: ``string``

The name of the controller (ex: Mission Pinball Framework).

controller_version
~~~~~~~~~~~~~~~~~~

Type: ``string``

The version of the controller (ex: 0.33.0).

Response
--------
When received by the media controller, this command automatically triggers a hard “reset”. If the
pin controller is sending this command, the media controller will respond with either its own
“hello” command, or the error “unknown protocol version.” The pin controller should never respond
to this command when it receives it from the media controller; that would trigger an infinite
loop.
