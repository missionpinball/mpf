"""Starts MPF's built-in media controller."""
# mc.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

from __future__ import print_function

import logging
from datetime import datetime
import socket
import os
from optparse import OptionParser
import errno
import sys

from mpf.media_controller.core.media_controller import MediaController
import version

# Allow command line options to do things
# We use optparse instead of argpase so python 2.6 works
parser = OptionParser()

parser.add_option("-C", "--mcconfigfile",
                  action="store", type="string", dest="mcconfigfile",
                  default=os.path.join("mpf", "media_controller",
                                       "mcconfig.yaml"),
                  help="The MPF framework config file")

parser.add_option("-c", "--configfile",
                  action="store", type="string", dest="configfile",
                  default="config.yaml",
                  help="Specifies the location of the first machine config "
                  "file")

parser.add_option("-l", "--logfile",
                  action="store", type="string", dest="logfile",
                  default=os.path.join("logs", datetime.now().strftime(
                  "%Y-%m-%d-%H-%M-%S-mc-" + socket.gethostname() + ".log")),
                  help="Specifies the name (and path) of the log file")

parser.add_option("-v", "--verbose",
                  action="store_const", dest="loglevel", const=logging.DEBUG,
                  default=logging.INFO, help="Enables verbose logging to the "
                  "log file")

parser.add_option("-V", "--verboseconsole",
                  action="store_true", dest="consoleloglevel",
                  default=logging.INFO,
                  help="Enables verbose logging to the console. Do NOT on "
                  "Windows platforms")

parser.add_option("-o", "--optimized",
                  action="store_true", dest="optimized", default=False,
                  help="Enables performance optimized game loop")

parser.add_option("-x", "--nohw",
                  action="store_false", dest="physical_hw", default=True,
                  help="Not used, but included since mpf.py uses it and people "
                  "keep adding -x by mistake.")

parser.add_option("--versions",
                  action="store_true", dest="version", default=False,
                  help="Shows the MC version and quits")

(options, args) = parser.parse_args()
options_dict = vars(options)  # convert the values instance to python dict

# if --version was passed, print the version and quit
if options_dict['version']:
    print("Mission Pinball Framework Media Controller Version:",
          version.__version__)
    print("Requires config file version:", version.__config_version__)
    print("Backbox Control Protocol (BCP) Version:", version.__bcp_version__)
    sys.exit()

# add the first positional argument into the options dict as the machine path
try:
    options_dict['machinepath'] = args[0]
except:
    print("Error: You need to specify the path to your machine_files folder "
          "for the game you want to run.")
    sys.exit()

# Configure logging. Creates a logfile and logs to the console.
# Formating options are documented here:
# https://docs.python.org/2.7/library/logging.html#logrecord-attributes

try:
    os.makedirs('logs')
except OSError as exception:
    if exception.errno != errno.EEXIST:
        raise

logging.basicConfig(level=options.loglevel,
                    format='%(asctime)s : %(levelname)s : %(name)s : %(message)s',
                    filename=options.logfile,
                    filemode='w')

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(options.consoleloglevel)

# set a format which is simpler for console use
formatter = logging.Formatter('%(levelname)s : %(name)s : %(message)s')

# tell the handler to use this format
console.setFormatter(formatter)

# add the handler to the root logger
logging.getLogger('').addHandler(console)


def main():
    try:
        mc = MediaController(options_dict)
        mc.run()
        logging.info("MC run loop ended.")
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
