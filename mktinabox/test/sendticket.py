import socket
import sys

s = socket.socket()
s.connect('localhost', 9100)

if len(sys.argv) > 1:
    f = open(str(sys.argv[1]), 'rb')
    ticket = f.read(1024)
    while ticket:
        s.send(ticket)
        ticket = f.read(1024)
    s.close()
