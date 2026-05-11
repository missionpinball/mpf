"""Command which launches both the MPF core engine and MPF-MC."""

from importlib import import_module
import argparse
import configparser
import shutil
import subprocess
import os
import re


def _start_mpf(mpf_path, machine_path, args):
    module = import_module('mpf.commands.game')
    module.Command(mpf_path, machine_path, args)


def _spawn_gmc(gmc_args, mpf_args):
    full_godot_exec_path = shutil.which(gmc_args.godot_exec_path)

    # Verify that the godot executable exists
    if not full_godot_exec_path:
        raise FileNotFoundError("Unable to find Godot executable at '%s'. Please check this file, "
                                "your PATH, or specify an executable with the -G argument." % gmc_args.godot_exec_path)

    full_gmc_project_path = os.path.join(gmc_args.gmc_project_path, "project.godot")
    try:
        os.stat(full_gmc_project_path)
    except FileNotFoundError:
        raise FileNotFoundError("Unable to find GMC project.godot file in '%s'. Please check this folder "
                                "or specify a project directory with the -g argument." % gmc_args.gmc_project_path)

    # Some args for MPF we'll borrow as well
    transferred_args = []
    # TODO: Refactor the ArgParse to use subparsers
    # and parent parsers to simplify the whole affair.
    verbose_regex = r'-[\w]*[vV]'
    if re.match(verbose_regex, " ".join(mpf_args)):
        transferred_args.append("-v")

    #pylint: disable-msg=consider-using-with
    subprocess.Popen(
        [full_godot_exec_path, *transferred_args],
        cwd=gmc_args.gmc_project_path
    )


class Command:

    """Command which runs game and gmc."""

    def __init__(self, mpf_path, machine_path, args):
        """Run game and gmc."""
        # First load a config file for possible default values
        config = configparser.ConfigParser(strict=False, allow_no_value=True)
        try:
            # It feels cleaner to use the same config file as GMC, even though the
            # name is misleading
            config_path = os.path.join(machine_path, "gmc.cfg")
            os.stat(config_path)
            config.read(config_path)
        except FileNotFoundError:
            pass

        parser = argparse.ArgumentParser(description='Starts MPF and GMC concurrently')

        parser.add_argument("-g",
                            action="store", dest="gmc_project_path",
                            default=config.get("cli", "gmc_project_path", fallback=machine_path).strip('\'"'),
                            help="Path to the GMC project folder, if not current directory.")

        parser.add_argument("-G",
                            action="store", dest="godot_exec_path",
                            default=config.get("cli", "godot_exec_path", fallback="godot").strip('\'"'),
                            help="Path to the Godot executable")

        parser.add_argument("-L",
                            action="store", dest="gmc_log_file",
                            metavar='gmc_log_file',
                            default=config.get("cli", "gmc_log_file", fallback=None),
                            help=argparse.SUPPRESS)

        # Parse the GMC-specific args and pass the leftovers to MPF
        gmc_args, mpf_args = parser.parse_known_args(args)

        _spawn_gmc(gmc_args, mpf_args)

        _start_mpf(mpf_path, machine_path, mpf_args)
