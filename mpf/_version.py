"""Version string of MPF.

This modules holds the MPF version strings, including the version of BCP it
needs and the config file version it needs.

It's used internally for all sorts of things, from printing the output of the
`mpf --version` command, to making sure any processes connected via BCP are
the proper versions, to automatically triggering new builds and deployments to
PyPI.

"""

__version__ = '0.31.11'
__short_version__ = '0.31'
__bcp_version__ = '1.0'
__config_version__ = '4'
__show_version__ = '4'

version = "MPF v{}".format(__version__)

extended_version = "MPF v{}, Config version:{}, Show version: {}, " \
                   "BCP version:{}".format(__version__, __config_version__,
                                           __show_version__, __bcp_version__)
