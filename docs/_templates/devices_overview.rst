Devices
=======

Instances of MPF devices, available at ``self.machine.*device_collection*.*device_name*``. For example, a flipper
device called "right_flipper" is at ``self.machine.flippers.right_flipper``, and a multiball called "awesome" is
accessible at ``self.machine.multiballs.awesome``.

Note that device collections are accessible as attributes and items, so the right flipper mentioned above is also
available to programmers at ``self.machine.flippers['right_flipper']``

.. toctree::

{devices}