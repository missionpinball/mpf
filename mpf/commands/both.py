"""Runs mc and game."""

from importlib import import_module
import multiprocessing


def _start_mpf(mpf_path, machine_path, args):
    module = import_module('mpf.commands.game')
    module.Command(mpf_path, machine_path, args)


def _start_mc(mpf_path, machine_path, args):
    module = import_module('mpfmc.commands.mc')
    module.Command(mpf_path, machine_path, args)


class Command(object):

    """Command which runs game and mc."""

    def __init__(self, mpf_path, machine_path, args):
        """Run game and mc."""
        multiprocessing.set_start_method('spawn')
        mpf = multiprocessing.Process(target=_start_mpf,
                                      args=(mpf_path, machine_path, args))
        mc = multiprocessing.Process(target=_start_mc,
                                     args=(mpf_path, machine_path, args))
        mpf.start()
        mc.start()
        mpf.join()
        mc.join()
