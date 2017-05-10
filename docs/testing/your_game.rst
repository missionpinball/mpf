Writing Unit Tests for Your Game
================================

It's possible to create unit tests which test the actual functionality of your MPF game. These tests are extremely
valuable *even if your game is just based on config files*.

For example, you can write a test that simulates starting a game and hitting a sequence of switches, then you can
check to make sure the a certain mode is running, or a light is the right color, or an achievement group is in the
proper state, etc. Then you can advance the time to timeout a mode and verify that the mode as stopped, etc, etc.

Here's how you can create a basic unit test for your machine.

If you want to see a real example, check out the tests from Gabe Knuth's *Brooks 'n Dunn* machine:

https://github.com/GabeKnuth/BnD/blob/master/tests/test_bnd.py

1. Add a tests folder to your machine folder
--------------------------------------------

todo