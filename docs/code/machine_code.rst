How to add machine-wide custom code
===================================

MPF contains a "Scriptlet" concept which lets you add custom code to your
game.

Scriptlets are Python modules that run at the "root" of your game. You can
use them to do anything you want.

Note that MPF also has the ability to run custom :doc:`mode code <mode_code>`
which is code that is associated with a certain game mode and is generally
only active when the mode it's in is active. So if you just want to write your
own custom game logic, you'll probably use mode code.

Scriptlets, on the other hand, are sort of "machine-level" custom code.
Scriptlets are nice if you have some kind of custom device type that doesn't
match up to any of MPF's built in devices. The elevator and claw unloader
in *Demolition Man* is a good example, and what we'll use here.

Here's how to create a scriptlet:

1. Create your scriptlet file
-----------------------------

First, add a ``scriptlets`` folder to your machine folder. Then inside there,
create the Python file that will hold your scriptlet. In the *Demo Man* example,
it looks like this:

.. image:: images/scriptlet.png

2. Open and edit your scriptlet file
------------------------------------

Next, edit the scriptlet file you created. At a bare minimum, you'll need this:

.. code-block:: python

   from mpf.core.scriptlet import Scriptlet


   class Claw(Scriptlet):
       pass

Note that MPF contains a ``Scriptlet`` base class which is very simple.
(You can see the source of it on GitHub `here <https://github.com/missionpinball/mpf/blob/dev/mpf/core/scriptlet.py>`_.)
We called our class ``Claw`` in this case.

Pretty much all this does is give you a reference to the main MPF machine
controller at ``self.machine``, as well as setup a delay manager you can use
and set the name of your scriptlet. There's also an ``on_load()`` method which
is called when the scriptlet is loaded which you can use in your own code.

3. Add the scriptlet to your machine config
-------------------------------------------

Next, edit your machine config file and add a ``scriptlets:`` section, then
under there add the module (file name) for your scriptlet, followed by a dot,
followed by the class name for your scriptlet.

For *Demo Man*, that looks like this:

.. code-block:: yaml

   scriptlets:
     - claw.Claw

4. Real-world example
---------------------

At this point you should be able to run your game, though nothing should
happen because you haven't added any code to your scriptlet.

Take a look at the final *Demo Man* claw scriptlet to see what we did there.
Since Scriptlets have access to ``self.machine`` and they load when MPF
loads, you can do anything you want in them.

.. code-block:: python

   """Claw controller Scriptlet for Demo Man"""

   from mpf.core.scriptlet import Scriptlet


   class Claw(Scriptlet):

       def on_load(self):

           self.auto_release_in_progress = False

           # if the elevator switch is active for more than 100ms, that means
           # a ball is there, so we want to get it and deliver it to the claw
           self.machine.switch_controller.add_switch_handler(
               's_elevator_hold', self.get_ball, ms=100)

           # This is a one-time thing to check to see if there's a ball in
           # the elevator when MPF starts, and if so, we want to get it.
           if self.machine.switch_controller.is_active('s_elevator_hold'):
               self.auto_release_in_progress = True
               self.get_ball()

           # We'll use the event 'light_claw' to light the claw, so in the
           # future all we have to do is post this event and everything else
           # will be automatic.
           self.machine.events.add_handler('light_claw', self.light_claw)

       def enable(self):
           """Enable the claw."""

           # move left & right with the flipper switches, and stop moving when
           # they're released

           self.machine.switch_controller.add_switch_handler(
               's_flipper_lower_left', self.move_left)
           self.machine.switch_controller.add_switch_handler(
               's_flipper_lower_left', self.stop_moving, state=0)
           self.machine.switch_controller.add_switch_handler(
               's_flipper_lower_right', self.move_right)
           self.machine.switch_controller.add_switch_handler(
               's_flipper_lower_right', self.stop_moving, state=0)

           # release the ball when the launch button is hit
           self.machine.switch_controller.add_switch_handler(
               's_ball_launch', self.release)

           # stop moving if the claw hits a limit switch
           self.machine.switch_controller.add_switch_handler(
               's_claw_position_1', self.stop_moving)

           # We can use this event for slides to explain what's going on for
           # the player.
           self.machine.events.post('claw_enabled')

       def disable(self):
           """Disable the claw."""

           self.stop_moving()

           # remove all the switch handlers
           self.machine.switch_controller.remove_switch_handler(
               's_flipper_lower_left', self.move_left)
           self.machine.switch_controller.remove_switch_handler(
               's_flipper_lower_left', self.stop_moving, state=0)
           self.machine.switch_controller.remove_switch_handler(
               's_flipper_lower_right', self.move_right)
           self.machine.switch_controller.remove_switch_handler(
               's_flipper_lower_right', self.stop_moving, state=0)
           self.machine.switch_controller.remove_switch_handler(
               's_ball_launch', self.release)
           self.machine.switch_controller.remove_switch_handler(
               's_claw_position_1', self.stop_moving)
           self.machine.switch_controller.remove_switch_handler(
               's_claw_position_1', self.release, state=0)
           self.machine.switch_controller.remove_switch_handler(
               's_claw_position_2', self.release)

           self.machine.events.post('claw_disabled')

       def move_left(self):
           """Start the claw moving to the left."""
           # before we turn on the driver to move the claw, make sure we're not
           # at the left limit
           if (self.machine.switch_controller.is_active('s_claw_position_2') and
                   self.machine.switch_controller.is_active('s_claw_position_1')):
               return
           self.machine.coils['c_claw_motor_left'].enable()

       def move_right(self):
           """Start the claw moving to the right."""
           # before we turn on the driver to move the claw, make sure we're not
           # at the right limit
           if (self.machine.switch_controller.is_active('s_claw_position_1') and
                   self.machine.switch_controller.is_inactive('s_claw_position_2')):
               return
           self.machine.coils['c_claw_motor_right'].enable()

       def stop_moving(self):
           """Stop the claw moving."""
           self.machine.coils['c_claw_motor_left'].disable()
           self.machine.coils['c_claw_motor_right'].disable()

       def release(self):
           """Release the ball by disabling the claw magnet."""
           self.disable_claw_magnet()
           self.auto_release_in_progress = False

           # Disable the claw since it doesn't have a ball anymore
           self.disable()

       def auto_release(self):
           """Aumatically move and release the ball."""
           # disable the switches since the machine is in control now
           self.disable()

           # If we're at the left limit, we need to move right before we can
           # release the ball.
           if (self.machine.switch_controller.is_active('s_claw_position_2') and
                   self.machine.switch_controller.is_active('s_claw_position_1')):
               self.machine.switch_controller.add_switch_handler(
                   's_claw_position_1', self.release, state=0)
               # move right, drop when switch 1 opens
               self.move_right()

           # If we're at the right limit, we need to move left before we can
           # release the ball
           elif (self.machine.switch_controller.is_active('s_claw_position_1') and
                   self.machine.switch_controller.is_inactive('s_claw_position_2')):
               self.machine.switch_controller.add_switch_handler(
                   's_claw_position_2', self.release)
               # move left, drop when switch 2 closes
               self.move_left()

           # If we're not at any limit, we can release the ball now.
           else:
               self.release()

       def get_ball(self):
           """Get a ball from the elevator."""

           # If there's no game in progress, we're going to auto pickup and
           # drop the ball with no player input

           if not self.machine.game:
               self.auto_release_in_progress = True

           # If the claw is not already in the ball pickup position, then move it
           # to the right.
           if not (self.machine.switch_controller.is_active('s_claw_position_1') and
                   self.machine.switch_controller.is_inactive('s_claw_position_2')):
               self.move_right()

               self.machine.switch_controller.add_switch_handler(
                   's_claw_position_1', self.do_pickup)

           # If the claw is in position for a pickup, we can do that pickup now
           else:
               self.do_pickup()

       def do_pickup(self):
           """Pickup a ball from the elevator"""
           self.stop_moving()
           self.machine.switch_controller.remove_switch_handler(
               's_claw_position_1', self.do_pickup)
           self.enable_claw_magnet()
           self.machine.coils['c_elevator_motor'].enable()
           self.machine.switch_controller.add_switch_handler('s_elevator_index',
                                                             self.stop_elevator)

           # If this is not an auto release, enable control of the claw for the
           # player
           if not self.auto_release_in_progress:
               self.enable()

       def stop_elevator(self):
           """Stop the elevator."""
           self.machine.coils['c_elevator_motor'].disable()

           if self.auto_release_in_progress:
               self.auto_release()

       def light_claw(self, **kwargs):
           """Lights the claw."""

           # Lighting the claw just enables the diverter so that the ball shot
           # that way will go to the elevator. Once the ball hits the elevator,
           # the other methods kick in to deliver it to the claw, and then once
           # the claw has it, the player can move and release it on their own.
           self.machine.diverters['diverter'].enable()

       def disable_claw_magnet(self):
           """Disable the claw magnet."""
           self.machine.coils['c_claw_magnet'].disable()

       def enable_claw_magnet(self):
           """Enable the claw magnet."""
           self.machine.coils['c_claw_magnet'].enable()
