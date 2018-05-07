Understanding the MPF boot up / start process
=============================================

A user runs "mpf" from the command line, which is registered as a console script entry point when MPF is installed.
That entry point calls the function ``run_from_command_line()`` in ``mpf.commands.__init__`` module.

That module parses the command line arguments, figures out the
machine path that's being executed, and figures out which MPF
command is being called. (MPF commands are things like "both" or "mc".)

Some commands are built-in to MPF (in the ``mpf/commands`` folder),
and others are registered as MPF via plugin entry points when other
packages are installed. (For example, MPF-MC registers the "mc"
command, the MPF Monitor registers the "monitor" command, etc.)

When you launch MPF (via ``mpf game`` or just plain ``mpf``), the
``mpf.commands.game`` module's ``Command`` class is instantiated.
This class processes the command line arguments, sets up logging,
and then creates an instance of the ``mpf.core.machine.MachineController``
class.

(This class is run inside a ``try:`` block, with all exceptions captured
and then sent to the log. This is how MPF is able to capture crashes
and stack traces into the log file when it crashes.

The Machine Controller
----------------------

The Machine Controller can be thought of as the main "kernel" of
MPF. It does a lot of things, including:

* Loading, merging, & validating the config files
* Setting up the clock
* Loading platform modules (based on what's used in the configs)
* Loading MPF core modules
* Loading MPF plugins
* Loading custom machine code
* Stepping through the initialization and reset phases
