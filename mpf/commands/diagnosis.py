"""Command to show diagnosis information about mpf and mc."""

import sys

from mpf._version import version as mpf_version


class Command(object):

    """Runs the mpf game."""

    def __init__(self, mpf_path, machine_path, args):
        """Run mpf diagnosis."""
        del mpf_path, machine_path, args
        print("MPF version: {}".format(mpf_version))
        try:
            from mpfmc._version import version as mc_version
            print("MPF-MC version: {}".format(mc_version))
        except:
            print("MPF-MC not found")
        sys.exit()
