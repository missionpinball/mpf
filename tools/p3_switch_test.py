import pinproc

proc = pinproc.PinPROC(pinproc.normalize_machine_type('pdb'))

for switch, state in enumerate(proc.switch_get_states()):

    if not switch % 16:
        print('')
        print(('SW-16 Board Address {0}'.format(switch / 16)))

    print(('Switch {0} State {1}'.format(switch, state)))
