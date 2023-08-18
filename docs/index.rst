Mission Pinball Framework |version| Developer Documentation
===========================================================

This is the developer documentation for the `Mission Pinball Framework <https://missionpinball.org>`_ (MPF), version
|version|. Click the "Read the Docs" link in the lower left corner for other versions & downloads.

This documentation is for people who want to want to add custom Python code & game logic to their machine and for
people who want to contribute to MPF itself.

.. note::

   **This is DEVELOPER documentation, not general USER documentation!**

   This documentation is for people writing custom Python code for MPF.
   If you're a general *user* of MPF, read the `MPF User Documentation <https://missionpinball.org>`_ instead.

Video about custom code in MPF:

.. youtube:: _BmvuCK5bV8

This developer documentation is broken into several sections:

Understanding the MPF codebase
------------------------------

* :doc:`overview/index`
* :doc:`overview/files`
* :doc:`overview/installation`
* :doc:`overview/boot_process`
* :doc:`overview/yaml`


Adding custom code to your machine
----------------------------------

* :doc:`code/index`
* :doc:`code/machine_code`
* :doc:`code/mode_code`

Common functions to use in your code
------------------------------------

* :doc:`functions/index`
* :doc:`functions/machine_variables`
* :doc:`functions/player_variables`

API Reference
-------------

* :doc:`api/machine_overview`
* :doc:`api/devices_overview`
* :doc:`api/modes_overview`
* :doc:`api/config_players_overview`
* :doc:`api/platforms_overview`
* :doc:`api/misc_overview`
* :doc:`api/tests_overview`

Writing Tests
-------------

* :doc:`testing/index`
* :doc:`testing/running_mpf_tests`
* :doc:`testing/writing_mpf_tests`
* :doc:`testing/writing_machine_tests`
* :doc:`testing/fuzz_testing`

Extending, Adding to, and Enhancing MPF
---------------------------------------

* :doc:`dev/index`
* :doc:`dev/dev_environment`
* :doc:`dev/plugins`
* :doc:`dev/hardware`

BCP Protocol
------------

* :doc:`bcp/index`

Index
-----

* We have an :doc:`index <genindex>` which lists all the classes, methods, and attributes in MPF across the board.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: DEVELOPER DOCUMENTATION

   Understanding the MPF codebase <overview/index>
   Adding custom code to your game <code/index>
   API Reference <api/index>
   Common Functions <functions/index>
   Writing Tests <testing/index>
   Extending MPF <dev/index>
   BCP Protocol <bcp/index>
   Method & Class Index <genindex>

.. toctree::
   :hidden:
   :caption: USER DOCUMENTATION

   User Documentation <https://missionpinball.org>
