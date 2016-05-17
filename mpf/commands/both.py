import os
import platform
import subprocess


class Command(object):
    def __init__(self, mpf_path, machine_path, args):
        del mpf_path
        if platform.system() == 'Windows':
            subprocess.Popen('mpf game {} {}'.format(machine_path,
                                                     ' '.join(args)))
            os.system('mpf mc {} {}'.format(machine_path, ' '.join(args)))

        else:
            if os.fork():
                os.system('mpf game {} {}'.format(
                    machine_path, ' '.join(args)))
            else:
                os.system('mpf mc {} {}'.format(
                    machine_path, ' '.join(args)))
