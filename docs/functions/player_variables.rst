Player Variables in Code
========================

Player variables are only accessible when a game is running.
Be prepared that the current player may change in a multiplayer game.

Inside a (game) mode you can access the current player using ``self.player``.
Alternatively, you can use ``self.machine.game.player`` but be aware that both
``self.machine.game`` and ``self.machine.game.player`` may be ``None``.

You can use player variables like this:

.. code-block:: python

   player = self.machine.game.player    # do not persist the player because it may change
                                        # alternatively use self.player in modes

   if not player:
      return    # do something reasonable here but do not crash in the next line

   # read player variable
   print(player["my_variable"])

   # set a variable
   player["my_variable"] = 17
