"""This is the main file you run to start a pinball machine."""
# mpf.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf
import logging
from datetime import datetime
import socket
import os
import argparse
import errno
import version
import sys

from mpf.system.machine import MachineController
from mpf.system.utility_functions import Util

parser = argparse.ArgumentParser(description='Starts the MPF core engine')

parser.add_argument("machine_path", help="Path of the machine folder.")

parser.add_argument("-C",
                    action="store", dest="mpfconfigfile",
                    default=os.path.join("mpf", "mpfconfig.yaml"),
                    help="The MPF framework default config file. Default is "
                    "mpf/mpfconfig.yaml")

parser.add_argument("-c",
                    action="store", dest="configfile",
                    default="config",
                    help="The name of a config file to load. Default is "
                    "config.yaml. Multiple files can be used via a comma-"
                    "separated list (no spaces between)")

parser.add_argument("-l",
                    action="store", dest="logfile",
                    default=os.path.join("logs", datetime.now().strftime(
                    "%Y-%m-%d-%H-%M-%S-mpf-" + socket.gethostname() + ".log")),
                    help="The name (and path) of the log file")

parser.add_argument("-v",
                    action="store_const", dest="loglevel", const=logging.DEBUG,
                    default=logging.INFO, help="Enables verbose logging to the"
                    " log file")

parser.add_argument("-V",
                    action="store_true", dest="consoleloglevel",
                    default=logging.INFO,
                    help="Enables verbose logging to the console. Do NOT on "
                    "Windows platforms. Must also use -v for this to work.")

parser.add_argument("-x",
                    action="store_const", dest="force_platform",
                    const='virtual', help="Forces the virtual platform to be "
                    "used for all devices")

parser.add_argument("-X",
                    action="store_const", dest="force_platform",
                    const='smart_virtual',
                    help="Forces the smart virtual platform to be used for all"
                    " devices")

parser.add_argument("-b",
                    action="store_false", dest="bcp", default=True,
                    help="Runs MPF without making a connection attempt to a "
                    "BCP Server")

parser.add_argument("--version",
                    action="version", version=version.version_str,
                    help="Displays the MPF, config file, and BCP version info "
                         "and exits")

args = parser.parse_args()
args.configfile = Util.string_to_list(args.configfile)

# Configure logging. Creates a logfile and logs to the console.
# Formatting options are documented here:
# https://docs.python.org/2.7/library/logging.html#logrecord-attributes

try:
    os.makedirs('logs')
except OSError as exception:
    if exception.errno != errno.EEXIST:
        raise

logging.basicConfig(level=args.loglevel,
                    format='%(asctime)s : %(levelname)s : %(name)s : %(message)s',
                    filename=args.logfile,
                    filemode='w')

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(args.consoleloglevel)

# set a format which is simpler for console use
formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')

# tell the handler to use this format
console.setFormatter(formatter)

# add the handler to the root logger
logging.getLogger('').addHandler(console)

def main():

    try:
        machine = MachineController(vars(args))
        machine.run()
        logging.info("MPF run loop ended.")
    except Exception, e:
        logging.exception(e)

    sys.exit()

if __name__ == '__main__':
    main()

# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
