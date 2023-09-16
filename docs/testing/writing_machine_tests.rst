Writing Custom Tests for your Machine
=====================================

As we already mentioned, the creators of MPF are HUGE believers in the value of automated testing. To that end,
MPF includes everything you need to write automated tests that test the logical functionality of your machine.
These tests are extremely valuable *even if your game is just based on config files*.

For example, you can write a test that simulates starting a game, launching a ball, hitting a sequence of switches,
and then verifying that a certain mode is running, or a light is the right color, or an achievement group is in the
proper state, etc. Then you can advance the time to timeout a mode and verify that the mode as stopped, etc, etc.

When you first start building your MPF config, you might think, "What's the point?"... especially with some of the
more simple tests. However your MPF config files will get complex pretty quickly, and often times you'll think you
have some mode done and working perfectly, but then a month later you change something that seems unrelated which
ends up breaking it. Unfortunately this usually happens without you knowing it, and by the time you realize that
something broke, more times has passed and it's hard to figure out what broke what.

So this is where unit tests come in! :)

If you write simple unit tests that test each new thing you add to an MPF config file, then over time you'll end
up with a huge library of tests for your game. If you get in the habit of running your tests often, then you'll
know right away if a change that you made broke something. (And you'll also know when everything is ok when all
your tests pass again!)

.. rubric:: Tutorial for writing your own tests

We have a complete tutorial which walks you through writing tests for your own machine. This tutorial
conveniently follows the general MPF tutorial at `<https://missionpinball.org/tutorial>`_. Each step here matches the
step with the same number there. (Just make sure you'll looking at the same version of the documentation
in both places.)

In the general MPF tutorial, each step builds on the previous to add more features to the config files for
the tutorial project. In the unit test tutorial (what you're reading here), each step shows you how to write
the unit tests which test the new features you just added to the tutorial machine.

You can follow along and learn here:

.. toctree::
   :maxdepth: 1

   tutorial/1
   tutorial/2