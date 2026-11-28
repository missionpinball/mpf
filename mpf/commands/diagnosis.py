"""Command to show diagnosis information about mpf and mc."""

import sys

from serial.tools import list_ports

from mpf._version import version as mpf_version


class Command:

    """Runs the mpf game."""

    def __init__(self, mpf_path, machine_path, args):
        """Run mpf diagnosis."""
        del args
        print("MPF version: {}".format(mpf_version))
        print("MPF install location: {}".format(mpf_path))
        print("Machine folder detected: {}".format(machine_path))

        print("\nSerial ports found:")
        iterator = list_ports.comports()
        for _, (port, desc, hwid) in enumerate(iterator, 1):
            sys.stdout.write("{:20}\n".format(port))
            sys.stdout.write("    desc: {}\n".format(desc))
            sys.stdout.write("    hwid: {}\n".format(hwid))

        sys.exit()
