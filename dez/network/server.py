import rel
from dez import io
from dez.logging import default_get_logger
from dez.network.connection import Connection

class SocketDaemon(object):
    def __init__(self, hostname, port, cb=None, b64=False, cbargs=[], certfile=None, keyfile=None, cacerts=None):
        self.log = default_get_logger("SocketDaemon")
        self.hostname = hostname
        self.port = port
        self.cb = cb
        self.cbargs = cbargs
        self.b64 = b64
        self.secure = bool(certfile)
        io.listen(self.port, self.reg_conn, certfile, keyfile, cacerts)

    def reg_conn(self, sock, addr):
        def cb():
            conn = Connection(addr, sock, b64=self.b64)
            if self.cb:
                self.cb(conn, *self.cbargs)
        return cb

    def start(self):
        rel.signal(2, rel.abort)
        rel.dispatch()
