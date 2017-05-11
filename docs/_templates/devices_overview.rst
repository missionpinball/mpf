Devices
=======

Instances of MPF devices, available at ``self.machine.*device_collection*.*device_name*``. For example, a flipper
device called "right_flipper" is at ``self.machine.flippers.right_flipper``, and a multiball called "awesome" is
accessible at ``self.machine.multiballs.awesome``.

Note that device collections are accessible as attributes and items, so the right flipper mentioned above is also
available to programmers at ``self.machine.flippers['right_flipper']``.

.. note::

   "Devices" in MPF are more than physical hardware devices. Many of the "game logic" components listed in the user
   documentation (achievements, ball holds, extra balls, etc.) are implemented as "devices" in MPF code. (So you can
   think of devices as being either physical or logical.)

Here's a list of all the device types in MPF, linked to their API references.

.. toctree::

{devices}