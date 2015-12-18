import socket
import sys

def handle_command( cmd ):
    print(( "Received command " + cmd ))

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = ('localhost', 5050)
print('starting up on %s port %s' % server_address, file=sys.stderr)
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

while True:
    # Wait for a connection
    print('waiting for a connection...\n\n', file=sys.stderr)
    connection, client_address = sock.accept()

    try:
        print('connection from', client_address, file=sys.stderr)

        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(255)
            if data:
                commands = data.decode("utf-8").split("\n")
                for cmd in commands:
                    if cmd:
                        handle_command( cmd )
            else:
                print('no more data from', client_address, file=sys.stderr)
                break

    finally:
        # Clean up the connection
        connection.close()
