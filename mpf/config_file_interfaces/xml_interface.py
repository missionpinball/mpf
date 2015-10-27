"""Contains the XmlInterface class for reading & writing to YAML files"""

# xml_interface.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import sys
import version

from mpf.system.config import Config