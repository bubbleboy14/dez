import event, ssl
from dez import io
from dez.logging import default_get_logger
from dez.network.connection import Connection

class SocketDaemon(object):
    def __init__(self, hostname, port, cb=None, b64=False, cbargs=[], certfile=None, keyfile=None):
        self.log = default_get_logger("SocketDaemon")
        self.hostname = hostname
        self.port = port
        self.sock = io.server_socket(self.port, certfile, keyfile)
        self.cb = cb
        self.cbargs = cbargs
        self.b64 = b64
        self.listen = event.read(self.sock, self.accept_connection)

    def accept_connection(self):
        try:
            sock, addr = self.sock.accept()
        except ssl.SSLError, e:
            self.log.info("abandoning connection on SSLError: %s"%(e,))
            return True
        conn = Connection(addr, sock, b64=self.b64)
        if self.cb:
            self.cb(conn, *self.cbargs)
        return True

    def start(self):
        event.signal(2, event.abort)
        event.dispatch()
