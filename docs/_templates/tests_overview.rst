Testing Class API
=================

MPF includes several unit test classes which you can use to
:doc:`write tests which test MPF </testing/writing_mpf_tests>` or to
:doc:`write tests for your own game </testing/your_game>`.

These tests include several MPF-specific assertion methods for things like modes, players, balls, device states, etc.,
as well as logic which advances the time and mocks the BCP and hardware connections.

You can add commands in your tests to "advance" the time which the MPF tests can test quickly, so you can test a complete
3-minute game play session in a few hundred milliseconds of real world time.

It might be helpful to look at the real internal tests that MPF uses (which all use these test classes) to get a feel
for how tests are written in MPF. They're available in the
`mpf/tests <https://github.com/missionpinball/mpf/tree/dev/mpf/tests>`_ folder in the MPF repository. (They're
installed locally when you install MPF.)

Here's a diagram which shows how all the MPF and MPF-MC test case classes relate to each other:

.. image:: /images/test_classes.png

And the API reference for each:

.. toctree::
   {tests}