import argparse
import os
import sys
from importlib import import_module

import mpf.core

EXAMPLES_FOLDER = 'examples'
CONFIG_FOLDER = 'config'


class CommandLineUtility(object):
    def __init__(self, path=None):

        self.argv = sys.argv[:]
        self.path = path
        self.mpf_path = os.path.abspath(os.path.join(mpf.core.__path__[0],
                                                     os.pardir))

    def check_python_version(self):
        if sys.version_info[0] != 3:
            print("MPF requires Python 3. You have Python {}.{}.{}".format(
                sys.version_info[0], sys.version_info[1], sys.version_info[2]
            ))
            sys.exit()

    def execute(self):
        """Actually runs the command that was just setup."""

        self.check_python_version()

        try:
            command = self.argv[1]
        except IndexError:
            command = 'both'

        try:
            module = import_module('mpf.commands.%s' % command)
            self.argv.pop(1)
        except (ImportError, IndexError):
            # assume we have a machine folder to run and not a command
            module = import_module('mpf.commands.both')

        machine_path, remaining_args = self.parse_args()

        return module.Command(self.mpf_path, machine_path,
                              remaining_args)

    def parse_args(self):

        parser = argparse.ArgumentParser(description='MPF Command')

        parser.add_argument("machine_path", help="Path of the machine folder.",
                            default=None, nargs='?')

        args, remaining_args = parser.parse_known_args(self.argv[1:])
        machine_path = self.get_machine_path(args.machine_path)

        return machine_path, remaining_args

    def get_machine_path(self, machine_path_hint):

        machine_path = None

        if machine_path_hint:
            if os.path.isdir(os.path.join(self.path, machine_path_hint)):
                # If the path hint resolves to a folder, use that as the
                # machine folder
                machine_path = os.path.join(self.path, machine_path_hint)

            else:
                # If the folder is invalid, see if we have an examples machine
                # folder with that name
                example_machine_path = os.path.abspath(os.path.join(
                    self.mpf_path, os.pardir, EXAMPLES_FOLDER,
                    machine_path_hint))

                if os.path.isdir(example_machine_path):
                    machine_path = example_machine_path

        else:
            # no path hint passed.
            # Is there a /config folder in our current folder? If so we assume
            # the current folder is the machine folder
            if os.path.isdir(os.path.join(self.path, CONFIG_FOLDER)):
                machine_path = self.path

        if machine_path:
            return machine_path
        else:
            print("Error. Could not find machine folder: '{}'.".format(
                machine_path_hint))
            sys.exit()


def run_from_command_line():
    path = os.path.abspath(os.path.curdir)
    CommandLineUtility(path).execute()
