"""Holds various Version strings of MPF.

This modules holds the MPF version strings, including the version of BCP it
needs and the config file version it needs.

It's used internally for all sorts of things, from printing the output of the
`mpf --version` command, to making sure any processes connected via BCP are
the proper versions, to automatically triggering new builds and deployments to
PyPI.

"""

__version__ = '0.57.1'  # Also consider whether MPF-MC pyproject.toml should be updated
'''The full version of MPF.'''

__short_version__ = '0.57'
'''The major.minor version of MPF.'''

__bcp_version__ = '1.1'
'''The version of BCP this build of MPF uses.'''

__config_version__ = '6'
'''The config file version this build of MPF uses.'''

__show_version__ = '6'
'''The show format version this build of MPF uses.'''

# pylint: disable-msg=invalid-name
version = "Mission Pinball Framework v{}".format(__version__)
'''A friendly version string for this build of MPF.'''
# TODO change back before mainlining

# pylint: disable-msg=invalid-name
extended_version = "Mission Pinball Framework v{}, Config version:{}, Show version: {}, " \
                   "BCP version:{}".format(__version__, __config_version__,
                                           __show_version__, __bcp_version__)
'''An extended version string that includes the MPF version, show version,
and BCP versions used in this build of MPF.'''

log_url = "https://missionpinball.org/logs"
# TODO make dynamic "https://docs.missionpinball.org/en/dev/logs/{}.html"

__api__ = ['version',
           '__short_version__',
           '__bcp_version__',
           '__config_version__',
           '__show_version__',
           'version',
           'extended_version',
           'log_url']
