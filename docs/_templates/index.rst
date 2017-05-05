Mission Pinball Framework |version| API Reference
=================================================

Welcome to MPF's API & developer reference! This documentation is for people who want to:

* Add custom Python code & game logic to their machine
* Help us write MPF itself

.. warning::

   **This is not general user documentation!**

   If you're a *user* of MPF, read the
   `MPF User Documentation <http://docs.missionpinball.org>`_ instead.

The developer documentation is broken into several sections:

.. rubric:: Machine

Core MPF machine components, accessible to programmers at ``self.machine.*name*``. For example, the ball controller
is at ``self.machine.ball_controller``, the event manager is ``self.machine.events``, etc.

.. rubric:: Devices

Instances of MPF devices, available at ``self.machine.*device_collection*.*device_name*``. For example, a flipper
device called "right_flipper" is at ``self.machine.flippers.right_flipper``, and a multiball called "awesome" is
accessible at ``self.machine.multiballs.awesome``.

Note that device collections are accessible as attributes and items, so the right flipper mentioned above is also
available to programmers at ``self.machine.flippers['right_flipper']``

.. rubric:: Modes

Covers all the "built-in" modes. They're accessible via ``self.machine.modes.*name*``, for example,
``self.machine.modes.game`` or ``self.machine.modes.base``.

.. rubric:: Config Players

Config players are available as machine attributes in the form of their player name plus ``_player``, for example,
``self.machine.light_player`` or ``self.machine.score_player``.

.. rubric:: Hardware Platforms

Hardware platforms are stored in a machine ``hardware_platforms`` dictionary, for example,
``self.machine.hardware_platforms['fast']`` or ``self.machine.hardware_platforms['p_roc']``.

.. rubric:: Index

We have an :ref:`genindex` which lists all the classes, methods, and attributes in MPF across the board.

.. toctree::
   :hidden:
   :caption: Machine

{machine}

.. toctree::
   :hidden:
   :caption: Devices

{devices}

.. toctree::
   :hidden:
   :caption: Modes

{modes}

.. toctree::
   :hidden:
   :caption: Config players

{config_players}

.. toctree::
   :hidden:
   :caption: Hardware Platforms

{platforms}
