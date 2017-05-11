BCP Protocol Specification
==========================

This document describes the Backbox Control Protocol, (or "BCP"), a
simple, fast protocol for communications between an implementation of
a pinball game controller and a multimedia controller.

.. note::

   BCP is how the MPF core engine and the MPF media controller communicate.

BCP transmits semantically relevant information and attempts to isolate
specific behaviors and identifiers on both sides. i.e., the pin controller is
responsible for telling the media controller “start multiball mode”. The pin
controller doesn't care what the media controller does with that information,
and the media controller doesn't care what happened on the pin controller
that caused the multiball mode to start.

BCP is versioned to prevent conflicts. Future versions of the BCP will be
designed to be backward compatible to every degree possible. The reference
implementation uses a raw TCP socket for communication. On localhost the
latency is usually sub-millisecond and on LANs it is under 10 milliseconds.
That means that the effect of messages is generally under 1/100th of a
second, which should be considered instantaneous from the perspective of
human perception.

It is important to note that this document specifies the details of the
protocol itself, not necessarily the behaviors of any specific
implementations it connects. Thus, there won’t be details about fonts or
sounds or images or videos or shaders here; those are up to specific
implementation being driven.

.. warning::
   Since the pin controller and media controller are both state
   machines synchronized through the use of commands, it is possible for
   the programmer to inadvertently set up infinite loops. These can be
   halted with the “reset” command or “hello” described below.

Background
----------

While the BCP protocol was created as part of the MPF project, the intention is
that BCP is an open protocol that could connect *any* pinball controller to *any*
media controller.

Protocol Format
---------------

+ Commands are human-readable text in a format similar to URLs, e.g.
  ``command?parameter1=value&parameter2=value``
+ Command characters are encoded with the utf-8 character encoding.
  This allows ad-hoc text for languages that use characters past ASCII-7
  bit, such as Japanese Kanji.
+ Command and parameter names are whitespace-trimmed on both ends by
  the recipient
+ Commands are case-insensitive
+ Parameters are optional. If present, a question mark separates the
  command from its parameters
+ Parameters are in the format ``name=value``
+ Parameter names are case-insensitive
+ Parameter values are case-sensitive
+ Simple parameter values are prefixed with a string that indicates
  their data type: (``int:``, ``float:``, ``bool:``, ``NoneType:``).  For example, the integer
  5 would appear in the command string as ``int:5``.
+ When a command includes one or more complex value types (list or dict)
  all parameters are encoded using JSON and the resulting encoded value
  is assigned to the ``json:`` parameter.
+ Parameters are separated by an ampersand (``&``)
+ Parameter names and their values are escaped using percent encoding
  as necessary; (`details here <https://en.wikipedia.org/wiki/Percent-encoding>`_).
+ Commands are terminated by a line feed character (``\n``). Carriage
  return characters (``\r``) should be tolerated but are not significant.
+ A blank line (no command) is ignored
+ Commands beginning with a hash character (``#``) are ignored
+ If a command passes unknown parameters, the recipient should ignore
  them.
+ The pinball controller and the media controller must be resilient to
  network problems; if a connection is lost, it can simply re-open it to
  resume operation. There is no requirement to buffer unsendable
  commands to transmit on reconnection.
+ Once initial handshaking has completed on the first connection,
  subsequent re-connects do not have to handshake again.
+ An unrecognized command results in an error response with the
  message “unknown command”

In all commands referenced below, the ``\n`` terminator is implicit. Some
characters in parameters such as spaces would really be encoded as ``%20`` (space)
in operation, but are left unencoded here for clarity.

Initial Handshake
-----------------

When a connection is initially established, the pinball controller
transmits the following command:

::

    hello?version=1.0

...where *1.0* is the version of the Backbox protocol it wants to
speak. The media controller may reply with one of two responses:

::

    hello?version=1.0

...indicating that it can speak the protocol version named, and
reporting the version it speaks, or

::

    error?message=unknown protocol version

...indicating that it cannot. How the pin controller handles this
situation is implementation-dependent.

BCP commands
------------

The following BCP commands have been defined (and implemented) in MPF:

.. toctree::
   :maxdepth: 1

   ball_end <ball_end>
   ball_start <ball_start>
   device <device>
   error <error>
   goodbye <goodbye>
   hello <hello>
   machine_variable <machine_variable>
   mode_start <mode_start>
   mode_stop <mode_stop>
   monitor_start <monitor_start>
   monitor_stop <monitor_stop>
   player_added <player_added>
   player_turn_start <player_turn_start>
   player_variable <player_variable>
   register_trigger <register_trigger>
   remove_trigger <remove_trigger>
   reset <reset>
   reset_complete <reset_complete>
   switch <switch>
   trigger <trigger>
