"""Deprecated command to start MPF game engine."""

import sys


class Command(object):
    def __init__(self, mpf_path, machine_path, args):
        print('"mpf core" has been renamed to "mpf game", so run that instead.')
        sys.exit()
