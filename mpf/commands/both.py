"""Command which launches both the MPF core engine and MPF-MC."""

from importlib import import_module
import multiprocessing


def _start_mpf(mpf_path, machine_path, args):
    module = import_module('mpf.commands.game')
    module.Command(mpf_path, machine_path, args)


def _start_mc(mpf_path, machine_path, args):
    module = import_module('mpfmc.commands.mc')
    module.Command(mpf_path, machine_path, args + ["--both"])


class Command:

    """Command which runs game and mc."""

    def __init__(self, mpf_path, machine_path, args):
        """Run game and mc."""
        multiprocessing.set_start_method('spawn')
        mc = multiprocessing.Process(target=_start_mc,
                                     args=(mpf_path, machine_path, args))
        mc.start()
        _start_mpf(mpf_path, machine_path, args)
        mc.join()
