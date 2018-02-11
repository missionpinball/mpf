How to add custom Python code to a game mode
============================================

The easiest and most common way to add custom Python code into your MPF game
is to add a code module to a mode folder. That lets you run code when that
mode is active and helps you break up any custom code you write per mode.

This "mode code" (as we call it) has access to the full MPF API. You can
post events, register event handlers which run custom things when events
are posted, access device state and control devices, read and set player
variables, post slides... really anything MPF can do, you can do.

Here's how you get started with custom mode code:

1. Create the module (file) to hold you code
--------------------------------------------

First, go into the folder where you want to create your custom code, and add
a "code" folder to that mode's folder. Then inside that folder, create a
file (we usually give this file the same name as the mode) with a ``.py``
extension.

For example, if you wanted to create custom code for your base mode, it would
look like this:

.. image:: /images/custom_mode_code.png

2. Open up the new Python file you just created
-----------------------------------------------

Next, open the new mode code Python file you just created and add the
bare minimum, which would look like this:

.. code-block:: python

   from mpf.core.mode import Mode

   class Base(Mode):
       pass

MPF includes a ``Mode`` class which acts as the base class for every mode
that runs in a game. That base class lives in the MPF package at
``mpf.core.mode``. You can see it online in GitHub
`here <https://github.com/missionpinball/mpf/blob/dev/mpf/core/mode.py>`_.

Notice that we named our custom class ``Base``. You can name it whatever you
want.

3. Update your mode config file to use the custom code
------------------------------------------------------

Once you create your custom mode code, you need to tell MPF that this mode
uses custom code instead of just the built-in code.

To do this, add a ``code:`` entry into the mode config file for the mode
where you're adding custom code. So in this case, that would be in the
/modes/base/config/base.yaml file, like this:

.. code-block:: yaml

   mode:
     start_events: ball_starting
     priority: 100
     code: base.Base

Note that the value for the ``code:`` section is the name of the Python module
(the file), then a dot, then the name of the class from that file. So in this
case, that's ``base.Base``.

4. Run your game!
-----------------

At this point you should be able to run your game and nothing should happen.
This is good, because if it doesn't crash, that means you did everything
right. :) Of course nothing special happens because you didn't actually add
any code to your custom mode code, so you won't see anything different.

5. Add some custom methods to do things
---------------------------------------

You can look at the Mode base class (the link from GitHub from earlier) to see
what the base Mode class does. However, we have created a few "convenience"
methods that you can use. They are:

   mode_init
      Called once when MPF is starting up

   mode_start
      Called every time the mode starts, just *after* the *mode_<name>_started*
      event is posted.

   mode_stop
      Called every time the mode stops, just *before* the *mode_<name>_stopping*
      event is posted.

   add_mode_event_handler
      This is the same as the main ``add_event_handler()`` method from the
      Event Manager, except since it's mode-specific it will *also*
      automatically remove any event handlers that you registered when the
      mode stops. (If you want to register event handlers that are always
      watching for events even when the mode is not running, you can use the
      regular ``self.machine.mode.add_handler()`` method.

You don't have to use all of these if you don't want to.

Also, modes have additional convenience attributes you can use within your
mode code:

   self.config
      A link to the config dictionary for the mode's config file.

   self.priority
      The priority the mode is running at. (Don't change this. Just read it.)

   self.delay
      An instance of the delay manager you can use to set delayed callbacks for
      this mode. Any active ones will be automatically removed when the mode
      ends.

   self.player
      A link to the current player object that's automatically updated when
      the player changes. This will be ``None`` if the mode is running outside
      of a game.

   self.active
      A boolean (True/False) value you can query to see if the mode is running.

6. Example usage
----------------
Here's an example of some mode code in use. This example is just a bunch of
random things, but again, since you're writing code here, the sky's the limit!
Seriously you could do all your game logic in mode code and not use the MPF
configs at all if you wanted to.

.. code-block:: python

   from mpf.core.mode import Mode


   class Base(Mode):

       def mode_init(self):
           print("My custom mode code is being initialized")

       def mode_start(self, **kwargs):
           # The mode_start method needs **kwargs because some events that
           # start modes pass additional parameters

           print("My custom mode code is starting")

           # call a delay in 5 seconds
           self.delay.add(5000, self.my_callback)

           # what player are we?
           print(self.player.number)

           # what's the player's score?
           print('Score: {}'.format(self.player.score))

           self.add_mode_event_handler('player_score', self.player_score_change)

           # turn LED "led01" red
           self.machine.leds.led01.color('red')

       def my_callback(self):
           print("My delayed call was just called!")

       def player_score_change(self, **kwargs):
           print("The new player's score is {}".format(self.player.score))

       def mode_stop(self, **kwargs):
           # The mode_stop method needs **kwargs because some events that
           # stop modes pass additional parameters

           print("My custom mode code is stopping")

You can use the API reference (or just look at the source code) to see what
options exist. Really you can do anything you want.
