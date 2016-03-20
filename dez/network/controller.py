import event
from dez.network.server import SocketDaemon
from dez.network.websocket import WebSocketDaemon
from dez.http.server import HTTPDaemon
from dez.http.application import HTTPApplication

def daemon_wrapper(dclass, *dargs):
    return lambda h, p, *args, **kwargs : dclass(h, p, *dargs)

heads = {
    "socket": SocketDaemon,
    "websocket": WebSocketDaemon,
    "http": daemon_wrapper(HTTPDaemon),
    "application": daemon_wrapper(HTTPApplication)
}

class SocketController(object):
    def __init__(self):
        self.daemons = {}

    def register_address(self, hostname, port, callback=None, cbargs=[], b64=False, daemon="socket", dclass=None):
        d = self.daemons.get((hostname, port))
        if d:
            d.cb = callback
            d.cbargs = cbargs
        else:
            dclass = dclass and daemon_wrapper(dclass) or heads[daemon]
            d = dclass(hostname, port, callback, b64, cbargs=cbargs)
            self.daemons[(hostname, port)] = d
        return d

    def _abort(self):
        if self.onstop:
            self.onstop()
        event.abort()

    def start(self, onstop=False):
        if not self.daemons:
            print "SocketController doesn't know where to listen. Use register_address(hostname, port, callback) to register server addresses."
            return
        self.onstop = onstop
        event.signal(2, self._abort)
        event.dispatch()
