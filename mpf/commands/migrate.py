"""Migrate YAML configuration files for MPF from one version to another."""

import argparse
import logging
import os
from datetime import datetime
import errno

from mpf.migrator.migrator import Migrator


class Command(object):

    """Run the migrator."""

    def __init__(self, mpf_path, machine_path, args):
        """Run the migrator."""
        parser = argparse.ArgumentParser(
            description='Migrates config and show files to the latest version')

        parser.add_argument("-v",
                            action="store_const", dest="consoleloglevel",
                            const=logging.DEBUG,
                            default=logging.INFO,
                            help="Enables verbose logging to the log file")

        parser.add_argument("-l",
                            action="store", dest="logfile",
                            metavar='file_name',
                            default=os.path.join(
                                "logs",
                                datetime.now().strftime(
                                    "migration-%Y-%m-%d-%H-%M-%S.log")),
                            help="The name (and path) of the log file")

        args = parser.parse_args(args)

        try:
            os.makedirs(os.path.join(machine_path, 'logs'))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        logging.basicConfig(level=logging.DEBUG,
                            format='%(name)s : %(message)s',
                            filename=os.path.join(machine_path, args.logfile),
                            filemode='w')

        # sys.stderr
        console = logging.StreamHandler()
        console.setLevel(args.consoleloglevel)

        # set a format which is simpler for console use
        formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')

        # tell the handler to use this format
        console.setFormatter(formatter)

        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

        Migrator(mpf_path, machine_path)
