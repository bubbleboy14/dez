import event
from dez.network.server import SocketDaemon
from dez.network.websocket import WebSocketDaemon
from dez.http.server import HTTPDaemon

def get_http(hostname, port, callback, b64, cbargs):
    return HTTPDaemon(hostname, port) # doesn't support extra args

heads = {
    "socket": SocketDaemon,
    "websocket": WebSocketDaemon,
    "http": get_http
}

class SocketController(object):
    def __init__(self):
        self.daemons = {}

    def register_address(self, hostname, port, callback=None, cbargs=[], b64=False, daemon="socket"):
        d = self.daemons.get((hostname, port))
        if d:
            d.cb = callback
            d.cbargs = cbargs
        else:
            d = heads[daemon](hostname, port, callback, b64, cbargs=cbargs)
            self.daemons[(hostname, port)] = d
        return d

    def start(self):
        if not self.daemons:
            print "SocketController doesn't know where to listen. Use register_address(hostname, port, callback) to register server addresses."
            return
        event.signal(2, event.abort)
        event.dispatch()
