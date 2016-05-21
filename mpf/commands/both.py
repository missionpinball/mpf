import os
import platform
import subprocess
from importlib import import_module


class Command(object):
    def __init__(self, mpf_path, machine_path, args):
        if platform.system() == 'Windows':
            subprocess.Popen('mpf game {} {}'.format(machine_path,
                                                     ' '.join(args)))
            os.system('mpf mc {} {}'.format(machine_path, ' '.join(args)))

        else:
            if os.fork():
                module = import_module('mpf.commands.game')
                module.Command(mpf_path, machine_path, args)
            else:
                module = import_module('mpfmc.commands.mc')
                module.Command(mpf_path, machine_path, args)
