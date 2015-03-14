"""Command line utility which sends OSC commands to an OSC host."""

# osc_sender.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import sys
from optparse import OptionParser
import socket

import OSC

server_ip = socket.gethostbyname(socket.gethostname())
server_port = 8000

address = None
data = None

parser = OptionParser()

parser.add_option("-s", "--server",
                  action="store", type="string", dest="server_ip",
                  default=server_ip,
                  help="OSC Server IP address. Default auto grabs the local IP.")

parser.add_option("-p", "--port",
                  action="store", type="int", dest="server_port",
                  default=server_port,
                  help="OSC Server Port. Default is 8000")

parser.add_option("-t", "--toggle",
                  action="store_true", dest="toggle",
                  default=False,
                  help="Means the OSC client will not send a second '0' data "
                        "message after the initial message")

(options, args) = parser.parse_args()
options = vars(options)

if len(args) != 2:
    print "Error: This tool requires two command-line arguments: OSC address & data"
    print "Example usage: python osc_sender.py /sw/shooter 1"
    sys.exit()
else:
    address, data = args

if not address.startswith('/'):
    address = '/' + address

osc_message = OSC.OSCMessage(address)
osc_message.append(data)

osc_client = OSC.OSCClient()
osc_client.connect((options['server_ip'], options['server_port']))

osc_client.send(osc_message)

if not options['toggle']:
    osc_message = OSC.OSCMessage(address)
    osc_message.append(0)
    osc_client.send(osc_message)

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
