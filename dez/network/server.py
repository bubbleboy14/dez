import event
from dez import io
from dez.network.connection import Connection

class SocketDaemon(object):
    def __init__(self, hostname, port, cb=None):
        self.hostname = hostname
        self.port = port
        self.sock = io.server_socket(self.port)
        self.cb = cb
        self.listen = event.read(self.sock,self.accept_connection)

    def accept_connection(self):
        sock, addr = self.sock.accept()
        conn = Connection(addr, sock)
        if self.cb:
            self.cb(conn)
        return True

    def start(self):
        event.signal(2,event.abort)
        event.dispatch()