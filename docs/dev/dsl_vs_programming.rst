Config files versus "real" programming
======================================

When we talk about MPF, we really play up the fact that when you use MPF, you
can do 90%+ of your of your "programming" with MPF's
:doc:`YAML configuration files </start/config_files>`.

We've received criticism of that over the past few years, typically falling into
one of the following categories:

* Since everything in MPF is in config files, that's something new you have to
  learn. If you don't know MPF, you can't just look at a config file and know
  what's happening.
* Since config files insulate the game programmer from the code, when something
  doesn't work, you don't know if it's your config or a bug in MPF.
* Using config files limits game programmers in that they have to do everything
  the "MPF way."
* Coding is fun! MPF deprives people of that.

We understand the motivation behind all these thoughts, so we'd like to
provide our perspective on these issues.

Why config files?
-----------------

At the most basic level, config files in MPF let you access hundreds or
thousands of lines of code with a simple line or two in a config. The actual
code that runs a pinball machine is really, really complex, especially when you
think about all the logic around ball tracking, mode stacking, multiple things
happening at once, etc.

By providing an interface like the config files, we allow you to have access and
to be able to control all these complex things in a simple way.

MPF's config files are a form of something in computer science called a
`"domain-specific language. (DSL)" <https://en.wikipedia.org/wiki/Domain-specific_language>`_

In this context the "domain" is pinball, so the MPF config files could be
thought of as a "pinball-specific language". This means that you can't use
the MPF DSL to program a dart board machine or a self-driving car, but when it
comes to programming pinball, they're darn good!

There are many advantages to DSLs, including:

+ Increased productivity: Get a complex mode up and running in MPF with a
  half-page config file instead of writing 500 lines of Python code.
+ Fewer bugs: The config files are used by lots of people, so we know they work
  the way they're supposed to, instead of every pinball maker writing their own
  stuff from scratch and re-solving the same problems over and over.
+ Easier to read: You can look at a few lines of config file and know what
  you're looking at and what it's trying to do versus pages of Python code that
  you have to reverse engineer to understand.
+ Ease of support: Same as above. If you are having a problem, it's easy to post
  a config to the forum and everyone can understand it, versus scanning through
  hundreds of lines of custom Python code.
+ Ease of planning: Since everyone in the MPF community speaks the same language
  of config files, it's easy to ask for help and direction on how to do things.
+ Insulation from future updates: The config files remain constant (or we
  provide migration tools to upgrade them, so we can make major changes to MPF
  under the hood without you having to re-write anything in your game.

Config files in MPF: use as much (or as little) as you want
-----------------------------------------------------------

Even though we just laid out the reasons we like "programming" your game via
config files instead of "real" code, there's one important thing to know about
the config files:

*You don't have to use config files for everything.*

MPF has a well-documented API, and you can easily mix code (written in Python or
the language of your choice) with existing MPF code and configs, so really you
can use as much or as little of the config file interface as you want.

One way to think about MPF is that it's a solid set of pinball functionality
with a nice API, and then the config file interface is a separate component that
rides on top of that API and exposes it via easy-to-use config files.

So if you're a programmer and prefer to program against the API directly, go for
it! The API is well-documented and fairly stable now, so if you
don't want to use a single config file for anything, you can just use the MPF
API and do whatever you want and still benefit from the thousands of hours of
effort we put into MPF.

The reality, though, is that building a complete game in MPF is a balance
between doing things in config files and writing code. At the end of the day,
it doesn't matter whether your game is 90% configs and 10% code, or 80/20,
50/50, 20/80, etc. The exact balance depends on the personal preference of the
person building the game.

In fact even we drop into "real" code to do certain things. There have been lots
of times when we think, "Yeah, X action would be 20 confusing config lines or
just two lines of Python, so I'm writing it in Python." That's perfectly fine.

The real power comes when you start to mix-and-match. For example, you could use
the MPF config files to build out your base hardware interface and mode
structures, then use your own Python code to do the logic within a mode, then
use your mode code to post an event to use MPF's scoring system, etc.

If you don't use MPF, then you have to write everything yourself in code. If you
do you MPF, then you get to choose what you write in code and what you don't
have to write. (Seriously, ball tracking is a hard. Use our pre-written code via
the config files!)

I already know Python. Why learn obscure config files?
------------------------------------------------------

Again, the software that runs pinball machines is complex. The complete MPF
codebase is over 15,000 lines of code, with thousands of lines of code to do
things that *seem* simple on the surface, like managing ball devices and
tracking where all the balls are at all times.

MPF's config files provide a friendly interface to all that complexity. So yes,
it's true that you have to spend a few hours learning about the ``ball_devices:``
section of the MPF config files in order to learn how to use them effectively.
But the alternative is learning everything about how ball tracking
works in a pinball machine and then writing all that from scratch yourself. That
would take a lot longer than it would to learn about how to configure ball
tracking in MPF. And besides, we already did that! :)

Aren't config files limiting?
-----------------------------

Even though we've tried to envision many different scenarios and many
different types of pinball machines as we built MPF, it's true that MPF does
things a certain way, and the config files are a manifestation of the way MPF
does things. So there could be scenarios where you want to do something
differently than how MPF does it.

But this does not mean that MPF is not the right framework for you. Don't throw
the baby out with the bath water! If you don't like the way something works in
MPF's shot management tracking, you don't have
to completely write your own shot management from scratch. Rather you can use
MPF's shot sytem, subclass the methods and objects you want to change, and
then tweak them to work in your specific scenario.

Even if you want to completely replace one component of MPF, there hundreds of
different components, modules, and systems that go into a pinball machine that
are already part of MPF. Unless you want to write all of those from scratch,
using MPF lets you get a head start on many of the things that you need in your
machine that you don't want to write yourself.

Coding is fun! Doesn't using config files deprive me of that?
-------------------------------------------------------------

Some people have said, "I like to code. I don't *want* to just build my machine
quickly." Certainly we appreciate that, because we like to code too!

If you decide to write the software for your own pinball machine from scratch,
you will spend hundreds of hours writing low-level pinball things, like
hardware device management, ball tracking, a mode queue, player objects, a
display and sound system, etc.

If you use MPF, even if you write your own game logic in Python code, then you
can focus on the fun stuff while the MPF developers focus on the boring
low-level pinball stuff.

Of course, if you're thinking, "But I *like* the low-level stuff, I want to
write that," then we would love to have you on our team helping to make MPF
better. :) We have a to-do list for MPF which will take years to complete, so if
you like to code, we'd love to have you help!

If there's something that MPF does that you don't like and that you think
you can do better, that's an even better reason to contribute back to MPF.
Please, help us make MPF better!

We have success stories of this already. Brian Madden and Gabe Knuth started
writing MPF in 2014. Since then, MPF user Jan Kantert started using MPF, and
then he started tweaking things here and there (and submitting his changes back
to the MPF project.) Now Jan has completely rewritten MPF's ball device code,
our hardware platform interface, he's added multiball, ball lock, and ball
search, extra balls, servos, tests... the list goes on.

Another MPF user, Quinn Capen, has rewritten MPF's RGB LED interface, written
a complete pinball-focused advanced audio system, written an alternative
media controller based on Unity 3D...

John Marsh said, "It would be cool if there was a GUI wizard to help people set
up their machines," so now he's building that.

Hugh Spahr created his own pinball controller hardware (the Open Pinball
Project), and then wrote a platform interface for MPF so MPF users can use OPP
hardware too.

You get the idea.

The bottom line is that these are all MPF users who love to code, so rather than
being scared away by MPF's config file interface, instead they embraced MPF, dug
in, and are making MPF better. So now all the time they spend writing code isn't
just limited to running on their machine which sits in their basement for 360
days a year; instead their code is running on pinball machines all over the
world, which is very fulfilling and cool!

When something breaks, I don't know if it's my config or an MPF bug?
--------------------------------------------------------------------

True, one of the limitations of using config files is that when things don't
work the way you expect, you don't know if it's a problem with your config or
a deeper bug in MPF.

However if you're someone who knows how to program, MPF is open source! You can
go through the MPF code to see if it's a bug, and if so, you can fix it and
submit a pull request to fix that bug for everyone.

And if it's a configuration error, you can also edit the MPF documentation to
be more clear, and then submit a pull request to the docs, and now you've also
helped fix this issue for everyone.

Again, don't not use MPF because it uses config files and you want to "know"
what's happening under the hood. Instead learn MPF and the code behind it and
share your programming and pinball passion with the world!

Using MPF means you have a team of programmers making your machine better
-------------------------------------------------------------------------

The MPF project was started in May 2014. Since then we have over 5,000 hours of
time spent (both in code and documentation). More importantly, we're continuing
to update and expand MPF, with dozens of commits to the core code and docs
every week. (Probably an average of 60 hours a week of work.)

If you use MPF, you get all that work for free. :) It's like having a team of
developers working 60 hours a week to make your game better. Pretty cool!

The bottom line
---------------

The creators of MPF are passionate about pinball, passionate about software
development, and passionate about open source.

The beauty of MPF is that it's a bunch of people, from all over the world,
writing software and documentation which helps more people create more pinball
machines. As MPF grows in popularity, we love the fact that some day we will be
able to walk into a bar, see a pinball machine, and know that some of the code
we wrote is powering that machine. It warms our hearts.

If you decide to go your own way and not use MPF, that's great. We support you!
(Feel free to rip off any ideas from MPF. We'd love it!) But don't write off MPF
just because you want to do "real" programming and MPF is a "config-based"
project. We could use the help of programmers like you. :)
