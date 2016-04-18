MPF API & Programmer's Reference
================================

This website contains the full API documentation for the Mission Pinball
Framework (and releated projects, such as *mpf-mc*, the Mission Pinball
Framework Media Controller).

It also includes information about how to extended the capabilities of MPF's
config file-based configuration, so you can customize your game.

Note that this is *not* the user documentation! If you're not a programmer and
you're new to MPF, use the main MPF user documentation website.

* MPF user documentation: `docs.missionpinball.com <http://docs.missionpinball.com>`_
* `Getting started with MPF <http://docs.missionpinball.com/0.30/intro/index.html>`_

Config files versus "real" programming
--------------------------------------

One of the misconceptions about MPF is that since most "programming" is done via
config files, it can't be extended in custom ways or that the config files are
limiting. In fact nothing is further from the truth! The config files in MPF
are a great way to get up and running, but if you're a "real" programmer and
want to do things in your machine that are not exposed in config files, or if
you simply prefer writing code, you can do so!

We explore this topic `in depth <http://docs.missionpinball.com/0.30/intro/config_files_vs_programming.html>`_
in the user documentation, so check out that link for details. The reality
though is that MPF's config files are a layer on top of the API that's detailed
on this site, so you're free to use the API directly for anything you want!
