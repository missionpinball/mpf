"""Command to start the MPF game engine."""

import argparse
import errno
import logging
import os
import socket
import sys
from datetime import datetime

from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util


class Command(object):

    """Runs the mpf game."""

    def __init__(self, mpf_path, machine_path, args):
        """Run mpf game."""
        parser = argparse.ArgumentParser(
            description='Starts the MPF game engine')

        parser.add_argument("-c",
                            action="store", dest="configfile",
                            default="config", metavar='config_file',
                            help="The name of a config file to load. Default "
                                 "is "
                                 "config.yaml. Multiple files can be used "
                                 "via a comma-"
                                 "separated list (no spaces between)")

        parser.add_argument("-v",
                            action="store_const", dest="loglevel",
                            const=logging.DEBUG,
                            default=logging.INFO,
                            help="Enables verbose logging to the"
                                 " log file")

        parser.add_argument("-V",
                            action="store_true", dest="consoleloglevel",
                            default=logging.INFO,
                            help="Enables verbose logging to the console. Do "
                                 "NOT on "
                                 "Windows platforms. Must also use -v for "
                                 "this to work.")

        parser.add_argument("-x",
                            action="store_const", dest="force_platform",
                            const='virtual',
                            help="Forces the virtual platform to be "
                                 "used for all devices")

        parser.add_argument("-a",
                            action="store_true", dest="no_load_cache",
                            help="Forces the config to be loaded from files "
                                 "and not "
                                 "cache")

        parser.add_argument("-A",
                            action="store_false", dest="create_config_cache",
                            help="Does not create the cache config files")

        parser.add_argument("-X",
                            action="store_const", dest="force_platform",
                            const='smart_virtual',
                            help="Forces the smart virtual platform to be "
                                 "used for all"
                                 " devices")

        parser.add_argument("-b",
                            action="store_false", dest="bcp", default=True,
                            help="Runs MPF without making a connection "
                                 "attempt to a "
                                 "BCP Server")

        parser.add_argument("-l",
                            action="store", dest="logfile",
                            metavar='file_name',
                            default=os.path.join("logs",
                                                 datetime.now().strftime(
                                                     "%Y-%m-%d-%H-%M-%S-mpf-" + socket.gethostname() + ".log")),
                            help="The name (and path) of the log file")

        parser.add_argument("-C",
                            action="store", dest="mpfconfigfile",
                            default=os.path.join(mpf_path,
                                                 "mpfconfig.yaml"),
                            metavar='config_file',
                            help="The MPF framework default config file. "
                                 "Default is "
                                 "mpf/mpfconfig.yaml")

        parser.add_argument("-p",
                            action="store_true", dest="pause", default=False,
                            help="Pause the terminal window on exit. Useful "
                            "when launching in a separate window so you can "
                            "see any errors before the window closes.")

        args = parser.parse_args(args)
        args.configfile = Util.string_to_list(args.configfile)

        # Configure logging. Creates a logfile and logs to the console.
        # Formatting options are documented here:
        # https://docs.python.org/2.7/library/logging.html#logrecord-attributes

        try:
            os.makedirs(os.path.join(machine_path, 'logs'))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        logging.basicConfig(level=args.loglevel,
                            format='%(asctime)s : %(levelname)s : %(name)s : '
                                   '%(message)s',
                            filename=os.path.join(machine_path, args.logfile),
                            filemode='w')

        # define a Handler which writes INFO messages or higher to the
        # sys.stderr
        console = logging.StreamHandler()
        console.setLevel(args.consoleloglevel)

        # set a format which is simpler for console use
        formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')

        # tell the handler to use this format
        console.setFormatter(formatter)

        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

        try:
            MachineController(mpf_path, machine_path, vars(args)).run()
            logging.info("MPF run loop ended.")
        # pylint: disable-msg=broad-except
        except Exception as e:
            logging.exception(e)

        if args.pause:
            input('Press ENTER to continue...')
        sys.exit()
