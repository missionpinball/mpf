"""Command to start the MPF game engine."""

import argparse
import errno
import os
import signal
import socket
import sys
from datetime import datetime
import logging
from logging.handlers import QueueHandler, SysLogHandler
import mpf.wire.fast.boards

from queue import Queue

from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util
from mpf.core.config_loader import YamlMultifileConfigLoader, ProductionConfigLoader
from mpf.commands.logging_formatters import JSONFormatter


class Command:

    """Runs the mpf game."""

    # pylint: disable-msg=too-many-locals,too-many-statements
    def __init__(self, mpf_path, machine_path, args):
        """Run mpf game."""
        del mpf_path
        self.machine = None
        self._sigint_count = 0

        parser = argparse.ArgumentParser(
            description='Generates wiring .yaml files')

        parser.add_argument("-c",
                    action="store", dest="configfile",
                    default="config.yaml", metavar='config_file',
                    help="The name of a config file to load. Default "
                         "is "
                         "config.yaml. Multiple files can be used "
                         "via a comma-"
                         "separated list (no spaces between)")

        self.args = parser.parse_args(args)
        self.args.configfile = Util.string_to_event_list(self.args.configfile)

        self.args.__dict__["production"] = False
        self.args.__dict__["force_platform"] = "smart_virtual"
        self.args.__dict__["text_ui"] = False
        self.args.__dict__["bcp"] = False


        config_loader = YamlMultifileConfigLoader(machine_path, self.args.configfile,
                                                      False, False)

        config = config_loader.load_mpf_config()

        print(config.get_machine_config())

        self.machine = MachineController(vars(self.args), config)
        self.machine.initialise_mpf()

        mpf.wire.fast.boards.wire(self.machine)


        # pylint: disable-msg=broad-except

