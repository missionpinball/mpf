"""Command line utility which sends OSC commands to an OSC host."""

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
    print("Error: This tool requires two command-line arguments: OSC address & data")
    print("Example usage: python osc_sender.py /sw/shooter 1")
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
