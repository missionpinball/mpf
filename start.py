# Judge Dredd main game code for Mission Pinball Framework
# This can be used as a template for other games

import logging
from datetime import datetime
import socket
import os
from optparse import OptionParser
import mpf.machine_controller

# Allow command line options to do things
# todo Should probably switch to argparse if we're targeting python 2.7+
parser = OptionParser()
parser.add_option("-c", "--configfile",
                  action="store", type="string", dest="configfile",
                  default=os.path.join("config", "config.yaml"),
                  help="Specifies the location of the first config file")

parser.add_option("-l", "--logfile",
                  action="store", type="string", dest="logfile",
                  default=os.path.join("logs", datetime.now().strftime(
                  "%Y-%m-%d-%H-%M-%S-sfpin-" + socket.gethostname() + ".log")),
                  help="Specifies the name (and path) of the log file")

parser.add_option("-v", "--verbose",
                  action="store_const", dest="loglevel", const=logging.DEBUG,
                  default=logging.INFO, help="Enables verbose logging")

parser.add_option("-x", "--nohw",
                  action="store_false", dest="physical_hw", default=True,
                  help="Specifies physical game hardware is not connected")

(options, args) = parser.parse_args()

# Configure logging. Creates a logfile and logs to the console.
# Formating options are documented here:
# https://docs.python.org/2.7/library/logging.html#logrecord-attributes
console_format = "%(asctime)s : %(name)s : %(message)s"
console_timestamp_format = "%H:%M:%S"
logfile_format = "%(asctime)s : %(name)s : %(message)s"


logging.basicConfig(level=options.loglevel, filename=options.logfile,
                    format=logfile_format, filemode='w')

console = logging.StreamHandler()
console.setLevel(options.loglevel)
console.setFormatter(logging.Formatter(fmt=console_format,
                                       datefmt=console_timestamp_format))
logging.getLogger('').addHandler(console)


def main():
    machine = mpf.MachineController(options.configfile, options.physical_hw)
    machine.run()

if __name__ == '__main__':
    main()
