import os
import platform


class Command(object):
    def __init__(self, mpf_path, machine_path, args):

        if platform.system() == 'Windows':
            os.system('start "MPF Core" mpf mc {} {} -p'.format(
                machine_path, ' '.join(args)))
            os.system('start "MPF Media Controller" mpf core {} {} -p'.format(
                machine_path, ' '.join(args)))

        else:
            # TODO I can't figure this out for non-Windows.
            # It's hard because we're accessing mpf via the console_script

            pass
