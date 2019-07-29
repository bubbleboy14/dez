import event
from dez import io
from dez.logging import default_get_logger
from dez.network.connection import Connection

class SocketDaemon(object):
    def __init__(self, hostname, port, cb=None, b64=False, cbargs=[], certfile=None, keyfile=None, cacerts=None):
        self.log = default_get_logger("SocketDaemon")
        self.hostname = hostname
        self.port = port
        self.sock = io.server_socket(self.port, certfile, keyfile, cacerts)
        self.cb = cb
        self.cbargs = cbargs
        self.b64 = b64
        self.secure = bool(certfile)
        self.listen = event.read(self.sock, self.accept_connection)

    def handshake_cb(self, sock, addr):
        def cb():
            conn = Connection(addr, sock, b64=self.b64)
            if self.cb:
                self.cb(conn, *self.cbargs)
        return cb

    def accept_connection(self):
        try:
            sock, addr = self.sock.accept()
            cb = self.handshake_cb(sock, addr)
            if self.secure:
                io.ssl_handshake(sock, cb)
                return True
        except io.socket.error as e:
            self.log.info("abandoning connection on socket error: %s"%(e,))
            return True
        cb()
        return True

    def start(self):
        event.signal(2, event.abort)
        event.dispatch()
