How to run MPF unittests
========================

Once MPF is installed, you can run some automated tests to make sure that
everything is working. To do this, open a command prompt, and then type the
following command and then press <enter>:

::

  python3 -m unittest discover mpf/tests

When you do this, you should see a bunch of dots on the screen (one for each
test that's run), and then when it's done, you should see a message showing
how many tests were run and that they were successful. The whole process should
take less a minute or so.

Note that ``mpf-mc`` must be installed as well as ``mpf`` for all tests to run. 
If it isn't, some tests will fail with the error "start took more than 20s", because 
MPF waited endlessly for the nonexistent media controller to be available.

(If you see any messages about some tests taking more than 0.5s, that's ok.)

The important thing is that when the tests are done, you should have a message
like this:

::

   Ran 587 tests in 27.121s

   OK

   C:\>

Note that the number of tests is changing all the time, so it probably won't
be exactly 587. And also the time they took to run will be different depending
on how fast your computer is.

These tests are the actual tests that the developers of MPF use to test MPF
itself. We wrote all these tests to make sure that updates and changes we add
to MPF don't break things. :) So if these tests pass, you know your MPF
installation is solid.

Remember though that MPF is actually two separate parts, the MPF game engine and
the MPF media controller. The command you run just tested the game engine, so
now let's test the media controller. To do this, run the following command
(basically the same thing as last time but with an "mc" added to the end, like
this):

::

  python3 -m unittest discover mpfmc/tests

(Note that ``mpfmc`` does not have a dash in it, like it did when you installed
it via *pip*.)

When you run the MPF-MC tests, you should see a graphical window pop up on the
screen, and many of the tests will put graphics and words in that window. Also,
some of the tests include audio, so if your speakers are on you should hear some
sounds at some point.

These tests take significantly longer (maybe 8x) than the MPF tests, but when they're done, that
graphical window should close, and you'll see all the dots in your command
window and a note that all the tests were successful.

Notes about the MPF-MC tests:

 * These tests create a window on the screen and then just re-use the same
   window for all tests (to save time). So don't worry if it looks like the
   window content is scaled weird or blurry or doesn't fill the entire window.

 * Many of these tests are used to test internal workings of
   the media controller itself, so there will be lots of time when the pop up
   window is blank or appears frozen since the tests are testing non-visual
   things.

 * The animation and transition tests include testing functionality to stop,
   restart, pause, and skip frames. So if things look "jerky" in the tests,
   don't worry, that doesn't mean your computer is slow, it's just how the
   tests work! :)
