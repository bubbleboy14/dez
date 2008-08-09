import event
from dez import io
from dez.network.connection import Connection

class SocketDaemon(object):
    def __init__(self, hostname, port, cb=None, b64=False):
        self.hostname = hostname
        self.port = port
        self.sock = io.server_socket(self.port)
        self.cb = cb
        self.b64 = b64
        self.listen = event.read(self.sock,self.accept_connection)

    def accept_connection(self):
        sock, addr = self.sock.accept()
        conn = Connection(addr, sock, b64=self.b64)
        if self.cb:
            self.cb(conn)
        return True

    def start(self):
        event.signal(2,event.abort)
        event.dispatch()