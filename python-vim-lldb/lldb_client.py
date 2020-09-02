import os
import sys
import socket
from time import sleep
import struct

HOST = ''
PORT = 65400

class Client(object):

    def __init__(self):
        numTries = 0
        self.isConnected = False
        while numTries < 3:
            try:
                self.s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s_conn.connect((HOST, PORT))
                l_onoff = 1
                l_linger = 0
                self.s_conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                        struct.pack('ii', l_onoff, l_linger))
                self.isConnected = True
                print('socket connected')
                return

            except OSError as error:
                print(error)
                print("Attempt %d of 100"% numTries)
                sleep(1)
                numTries += 1

        return -1

    def close(self):
        self.s_conn.close()
        self.isConnected = False

    def sendRequest(self, msg):
        if msg == '':
            return None

        self.s_conn.sendall(msg.encode())

        " XXX once we know the stand alone server is worth it, need to:        "
        " move receive to a select/poll and check if string starts with error: "
        " implement pager on longer data "
        data = self.s_conn.recv(14444)
        print(data.decode())



def startClient():
    """ simple client to query lldb server """
    client = Client()

    
    while True:
        try:
            input_str = input("(lldb) ")
            if len(input_str) < 1:
                    continue
            client.sendRequest(input_str)
        except EOFError:
            # TODO shutdown gracefully
            print('closing lldb')
            client.close()

    """
    for line in sys.stdin:
        client.sendRequest(line)
        """

startClient()


