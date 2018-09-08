"""MPF CLI commands."""
import argparse
from importlib import import_module
import os
import sys
from pkg_resources import iter_entry_points


import mpf.core
from mpf._version import version

EXAMPLES_FOLDER = 'examples'
CONFIG_FOLDER = 'config'


class MpfCommandLineParser:

    """Base class for cli commands."""

    def __init__(self, args, path):
        """Initialise CLI entry point."""
        self.argv = args
        self.path = path
        self.mpf_path = os.path.abspath(os.path.join(mpf.core.__path__[0],
                                                     os.pardir))

    def get_machine_path(self, machine_path_hint=None):
        """Find the full machine path based on the current directory and option hint.

        Args:
            machine_path_hint: Helps MPF locate the machine path. If None,
                the 'config' folder in the current working directory is used.

        Returns:
            String of full path of the machine folder that was located.
        """
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
            if machine_path_hint:
                wrong_path = os.path.abspath(machine_path_hint)
            else:
                wrong_path = os.path.abspath(os.curdir)

            raise AssertionError("Error: Could not find machine in folder: '{}'. "
                                 "Either start MPF from within your machine root folder or provide the path after the "
                                 "command.".format(wrong_path))

    def parse_args(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description='MPF Command')

        parser.add_argument("machine_path", help="Path of the machine folder.",
                            default=None, nargs='?')

        parser.add_argument("--version",
                            action="version", version=version,
                            help="Displays the MPF, config file, and BCP "
                                 "version info and exits")

        # the problem with parser.add_argument is it will take the first
        # positional argument it finds for machine_path and set it to the
        # machine path, regardless of what's in front of it. So for example,
        # args of "-c step4" will lead to machine_path='step4', but that's not
        # right, machine_path should be None. But this is because it doesn't
        # know that -c wants to consume the next positional arg.

        # So our workaround is we check if there are any argv, and if so, we
        # check to see if the first one starts with a dash, meaning it's an
        # optional arg and guaranteeing that whatever's after it is NOT our
        # machine path, so in that case, we just insert a None as the machine
        # path in front of it and everything is cool.

        if len(self.argv) > 1 and self.argv[1].startswith('-'):
            self.argv.insert(1, None)

        args, remaining_args = parser.parse_known_args(self.argv[1:])
        machine_path = self.get_machine_path(args.machine_path)

        return machine_path, remaining_args


class CommandLineUtility(MpfCommandLineParser):

    """Default CLI entry point."""

    def __init__(self, path=None):
        """Initialise CLI entry point."""
        super().__init__(path=path, args=sys.argv[:])
        self.external_commands = dict()
        self.get_external_commands()

    def get_external_commands(self):
        """Entry point to hook more commands.

        This is used from mpf mc.
        """
        for entry_point in iter_entry_points(group='mpf.command', name=None):
            command, function_ref = entry_point.load()()
            self.external_commands[command] = function_ref

    @classmethod
    def check_python_version(cls):
        """Check that we have at least Python 3."""
        if sys.version_info[0] != 3:
            print("MPF requires Python 3. You have Python {}.{}.{}".format(
                sys.version_info[0], sys.version_info[1], sys.version_info[2]
            ))
            sys.exit()

    def execute(self):
        """Execute the command that was just set up."""
        self.check_python_version()

        commands = set()

        for file in os.listdir(os.path.join(self.mpf_path, 'commands')):
            commands.add(os.path.splitext(file)[0])

        command = 'game'

        if len(self.argv) > 1:

            if self.argv[1] in self.external_commands:
                command = self.argv.pop(1)
                self.external_commands[command](self.mpf_path,
                                                *self.parse_args())
                return
            elif self.argv[1] in commands:
                command = self.argv.pop(1)

        _module = import_module('mpf.commands.%s' % command)

        if hasattr(_module, "subcommand") and _module.subcommand:
            _module.Command(self.argv, self.path)
        else:
            machine_path, remaining_args = self.parse_args()

            _module.Command(self.mpf_path, machine_path, remaining_args)


def run_from_command_line(args=None):
    """Run a CLI command.

    Args:
        args: Command line arguments that were passed.

    """
    del args
    path = os.path.abspath(os.path.curdir)
    CommandLineUtility(path).execute()
