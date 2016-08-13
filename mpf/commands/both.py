import os
import platform
import subprocess
from importlib import import_module
import sys


class Command(object):
    def __init__(self, mpf_path, machine_path, args):
        if platform.system() == 'Windows':
            game_cmd = [sys.executable, "-m", "mpf", "game", machine_path]
            game_cmd.extend(args)
            game = subprocess.Popen(game_cmd)

            mc_cmd = [sys.executable, "-m", "mpf", "mc", machine_path]
            mc_cmd.extend(args)
            mc = subprocess.Popen(mc_cmd)

            game.wait()
            mc.wait()

        else:
            if os.fork():
                module = import_module('mpf.commands.game')
                module.Command(mpf_path, machine_path, args)
            else:
                module = import_module('mpfmc.commands.mc')
                module.Command(mpf_path, machine_path, args)
