import os
import platform


class Command(object):
    def __init__(self, mpf_path, machine_path, args):
        del mpf_path
        if platform.system() == 'Windows':
            os.system('start "MPF Core" mpf mc {} {} -p'.format(
                machine_path, ' '.join(args)))
            os.system('start "MPF Media Controller" mpf game {} {} -p'.format(
                machine_path, ' '.join(args)))

        else:
            if os.fork():
                os.system('mpf game {} {}'.format(
                    machine_path, ' '.join(args)))
            else:
                os.system('mpf mc {} {}'.format(
                    machine_path, ' '.join(args)))
