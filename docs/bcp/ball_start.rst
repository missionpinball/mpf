ball_start (BCP command)
========================

Indicates a new ball has started. It passes the player number (1, 2, etc.) and the ball number
as parameters. This command will be sent every time a ball starts, even if the same player is
shooting again after an extra ball.

Origin
------
Pin controller

Parameters
----------

player_num
~~~~~~~~~~

Type: ``int``

The player number.

ball
~~~~

Type: ``int``

The ball number.

Response
--------
None

