"""BCP Server interface for the MPF Media Controller"""
# bcp_server.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# The Backbox Control Protocol was conceived and developed by:
# Quinn Capen
# Kevin Kelm
# Gabe Knuth
# Brian Madden
# Mike ORourke

# Documentation and more info at http://missionpinball.com/mpf

import logging
import socket
import sys
import threading
import time
import traceback


class BCPServer(threading.Thread):
    """Parent class for the BCP Server thread.

    Args:
        mc: A reference to the main MediaController instance.
        receiving_queue: A shared Queue() object which holds incoming BCP
            commands.
        sending_queue: A shared Queue() object which holds outgoing BCP
            commands.

    """

    def __init__(self, mc, receiving_queue, sending_queue):

        threading.Thread.__init__(self)
        self.mc = mc
        self.log = logging.getLogger('BCP')
        self.receive_queue = receiving_queue
        self.sending_queue = sending_queue
        self.connection = None
        self.socket = None
        self.done = False

        self.setup_server_socket()

        self.sending_thread = threading.Thread(target=self.sending_loop)
        self.sending_thread.daemon = True
        self.sending_thread.start()

    def setup_server_socket(self, interface='localhost', port=5050):
        """Sets up the socket listener.

        Args:
            interface: String name of which interface this socket will listen
                on.
            port: Integer TCP port number the socket will listen on.

        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.log.info('Starting up on %s port %s', interface, port)

        try:
            self.socket.bind((interface, port))
        except IOError:
            self.log.critical('Socket bind IOError')
            raise

        self.socket.listen(1)

    def run(self):
        """The socket thread's run loop."""

        try:
            while True:
                self.log.info("Waiting for a connection...")
                self.mc.events.post('client_disconnected')
                self.mc.pc_connected = False
                self.connection, client_address = self.socket.accept()

                self.log.info("Received connection from: %s:%s",
                              client_address[0], client_address[1])
                self.mc.events.post('client_connected',
                                    address=client_address[0],
                                    port=client_address[1])
                self.mc.pc_connected = True

                # Receive the data in small chunks and retransmit it
                while True:
                    try:
                        data = self.connection.recv(4096)
                        if data:
                            commands = data.split("\n")
                            for cmd in commands:
                                if cmd:
                                    self.process_received_message(cmd)
                        else:
                            # no more data
                            break

                    except:
                        if self.mc.config['media_controller']['exit_on_disconnect']:
                            self.mc.shutdown()
                        else:
                            break

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.mc.crash_queue.put(msg)

    def stop(self):
        """ Stops and shuts down the BCP server."""
        if not self.done:
            self.log.info("Socket thread stopping.")
            self.sending_queue.put('goodbye')
            time.sleep(1)  # give it a chance to send goodbye before quitting
            self.done = True
            self.mc.done = True

    def sending_loop(self):
        """Sending loop which transmits data from the sending queue to the
        remote socket.

        This method is run as a thread.
        """
        try:
            while not self.done:
                msg = self.sending_queue.get()

                if not msg.startswith('dmd_frame'):
                    self.log.debug('Sending "%s"', msg)

                try:
                    self.connection.sendall(msg + '\n')
                except (AttributeError, socket.error):
                    pass
                    # Do we just keep on trying, waiting until a new client
                    # connects?

            self.socket.close()
            self.socket = None

            self.mc.socket_thread_stopped()

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.mc.crash_queue.put(msg)

    def process_received_message(self, message):
        """Puts a received BCP message into the receiving queue.

        Args:
            message: The incoming BCP message

        """
        self.log.debug('Received "%s"', message)
        self.receive_queue.put(message)


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
