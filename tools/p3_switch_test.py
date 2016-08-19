"""Switch test for P3."""
import sys

try:    # pragma: no cover
    import pinproc
    pinproc_imported = True
except ImportError:     # pragma: no cover
    try:
        if sys.platform == 'darwin':
            from mpf.platforms.pinproc.osx import pinproc
        elif sys.platform == 'win32':
            if sys.platform.architecture()[0] == '32bit':
                from mpf.platforms.pinproc.x86 import pinproc
            elif sys.platform.architecture()[0] == '64bit':
                from mpf.platforms.pinproc.x64 import pinproc

        pinproc_imported = True

    except ImportError:
        pinproc_imported = False
        pinproc = None

proc = pinproc.PinPROC(pinproc.normalize_machine_type('pdb'))

for switch, state in enumerate(proc.switch_get_states()):

    if not switch % 16:
        print('')
        print('SW-16 Board Address {0}'.format(switch / 16))

    if state != 3:
        print('Switch {0} State {1}'.format(switch, state))
