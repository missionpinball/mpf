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
from queue import Queue

from mpf.core.machine import MachineController
from mpf.core.utility_functions import Util
from mpf.commands.logging_formatters import JSONFormatter


class Command:

    """Runs the mpf game."""

    # pylint: disable-msg=too-many-locals,too-many-statements
    def __init__(self, mpf_path, machine_path, args):
        """Run mpf game."""
        self.machine = None
        self._sigint_count = 0

        parser = argparse.ArgumentParser(
            description='Starts the MPF game engine')

        parser.add_argument("-a",
                            action="store_true", dest="no_load_cache",
                            help="Forces the config to be loaded from files "
                                 "and not cache")

        parser.add_argument("-A",
                            action="store_false", dest="create_config_cache",
                            help="Does not create the cache config files")

        parser.add_argument("-b",
                            action="store_false", dest="bcp", default=True,
                            help="Runs MPF without making a connection "
                                 "attempt to a "
                                 "BCP Server")

        parser.add_argument("-c",
                            action="store", dest="configfile",
                            default="config.yaml", metavar='config_file',
                            help="The name of a config file to load. Default "
                                 "is "
                                 "config.yaml. Multiple files can be used "
                                 "via a comma-"
                                 "separated list (no spaces between)")

        parser.add_argument("-C",
                            action="store", dest="mpfconfigfile",
                            default=os.path.join(mpf_path,
                                                 "mpfconfig.yaml"),
                            metavar='config_file',
                            help="The MPF framework default config file. "
                                 "Default is "
                                 "mpf/mpfconfig.yaml")

        parser.add_argument("-f",
                            action="store_true", dest="force_assets_load",
                            default=False,
                            help="Load all assets upon startup.  Useful for "
                            "ensuring all assets are set up properly "
                            "during development.")

        parser.add_argument("--json-logging",
                            action="store_true", dest="jsonlogging",
                            default=False,
                            help="Enables json logging to file. ")

        parser.add_argument("-l",
                            action="store", dest="logfile",
                            metavar='file_name',
                            default=os.path.join(
                                "logs",
                                datetime.now().strftime(
                                    "%Y-%m-%d-%H-%M-%S-mpf-" +
                                    socket.gethostname() + ".log")),
                            help="The name (and path) of the log file")

        parser.add_argument("-p",
                            action="store_true", dest="pause", default=False,
                            help="Pause the terminal window on exit. Useful "
                            "when launching in a separate window so you can "
                            "see any errors before the window closes.")

        parser.add_argument("-P",
                            action="store_true", dest="production", default=False,
                            help="Production mode. Will suppress errors, wait for hardware on start and "
                                 "try to exit when startup fails. Run this inside a loop.")

        parser.add_argument("-t",
                            action="store_false", dest='text_ui', default=True,
                            help="Use the ASCII test-based UI")

        parser.add_argument("-v",
                            action="store_const", dest="loglevel",
                            const=logging.DEBUG,
                            default=15,
                            help="Enables verbose logging to the"
                                 " log file")

        parser.add_argument("-V",
                            action="store_const", dest="consoleloglevel",
                            const=logging.DEBUG,
                            default=logging.INFO,
                            help="Enables verbose logging to the console. DO "
                                 "NOTE: On Windows platforms you must also use -v for "
                                 "this to work.")

        parser.add_argument("-x",
                            action="store_const", dest="force_platform",
                            const='virtual',
                            help="Forces the virtual platform to be "
                                 "used for all devices")

        parser.add_argument("--vpx",
                            action="store_const", dest="force_platform",
                            const='virtual_pinball',
                            help="Forces the virtual_pinball platform to be "
                                 "used for all devices")

        parser.add_argument("--syslog_address",
                            action="store", dest="syslog_address",
                            help="Log to the specified syslog address. This "
                                 "can be a domain socket such as /dev/og on "
                                 "Linux or /var/run/syslog on Mac. "
                                 "Alternatively, you an specify host:port for "
                                 "remote logging over UDP.")

        parser.add_argument("-X",
                            action="store_const", dest="force_platform",
                            const='smart_virtual',
                            help="Forces the smart virtual platform to be "
                                 "used for all"
                                 " devices")

        # The following are just included for full compatibility with mc
        # which is needed when using "mpf both".

        parser.add_argument("-L",
                            action="store", dest="mc_file_name",
                            metavar='mc_file_name',
                            default=None, help=argparse.SUPPRESS)

        parser.add_argument("--no-sound",
                            action="store_true", dest="no_sound", default=False)

        self.args = parser.parse_args(args)
        self.args.configfile = Util.string_to_list(self.args.configfile)

        # Configure logging. Creates a logfile and logs to the console.
        # Formatting options are documented here:
        # https://docs.python.org/2.7/library/logging.html#logrecord-attributes

        try:
            os.makedirs(os.path.join(machine_path, 'logs'))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        full_logfile_path = os.path.join(machine_path, self.args.logfile)

        try:
            os.remove(full_logfile_path)
        except OSError:
            pass

        if self.args.text_ui:
            console_log = logging.NullHandler()
            console_log.setLevel(logging.ERROR)
        else:
            console_log = logging.StreamHandler()
            console_log.setLevel(self.args.consoleloglevel)

        # tell the handler to use this format
        console_log.setFormatter(logging.Formatter(
            '%(levelname)s : %(name)s : %(message)s'))

        # initialise async handler for console
        console_log_queue = Queue()
        console_queue_handler = QueueHandler(console_log_queue)
        self.console_queue_listener = logging.handlers.QueueListener(
            console_log_queue, console_log)
        self.console_queue_listener.start()

        # initialise file log
        file_log = logging.FileHandler(full_logfile_path)
        if self.args.jsonlogging:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(name)s : %(message)s')
        file_log.setFormatter(formatter)

        # initialise async handler for file log
        file_log_queue = Queue()
        file_queue_handler = QueueHandler(file_log_queue)
        self.file_queue_listener = logging.handlers.QueueListener(
            file_log_queue, file_log)
        self.file_queue_listener.start()

        # add loggers
        logger = logging.getLogger()
        logger.addHandler(console_queue_handler)
        logger.addHandler(file_queue_handler)
        logger.setLevel(self.args.loglevel)

        if self.args.syslog_address:
            try:
                host, port = self.args.syslog_address.split(":")
            except ValueError:
                syslog_logger = SysLogHandler(self.args.syslog_address)
            else:
                syslog_logger = SysLogHandler((host, int(port)))

            logger.addHandler(syslog_logger)

        signal.signal(signal.SIGINT, self.sigint_handler)
        try:
            self.machine = MachineController(mpf_path, machine_path, vars(self.args))
            self.machine.add_crash_handler(self.restore_logger)
            self.machine.run()
            logging.info("MPF run loop ended.")
            self.exit()

        # pylint: disable-msg=broad-except
        except Exception as e:
            self.exit(exception=e)

    def sigint_handler(self, signum=None, frame=None):
        """Handle SIGINT."""
        del signum, frame
        self._sigint_count += 1
        if self._sigint_count > 1:
            self.exit("Received second SIGINT. Will exit ungracefully!")
        elif self.machine:
            self.machine.stop("SIGINT or keyboard interrupt")
        else:
            self.exit("Shutdown because of SIGINT or keyboard interrupt.")

    def restore_logger(self):
        """Restore logger."""
        if self.args.text_ui:
            # Re-enable console logging
            logger = logging.getLogger()
            logger.addHandler(logging.StreamHandler())

    def exit(self, exception=None):
        """Handle MPF exit from either a clean shutdown or from a crash.

        Cleanly shuts down logging and restores the console window if the Text
        UI option is used.
        """
        if exception:
            logging.exception(exception)

        logging.shutdown()
        self.console_queue_listener.stop()
        self.file_queue_listener.stop()

        if self.args.pause:
            input('Press ENTER to continue...')     # nosec

        sys.exit()
