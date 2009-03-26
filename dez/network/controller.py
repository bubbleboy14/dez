import event
from dez.network.server import SocketDaemon

class SocketController(object):
    def __init__(self):
        self.daemons = {}

    def register_address(self, hostname, port, callback, cbargs=[], b64=False):
        if (hostname, port) in self.daemons:
            self.daemons[(hostname, port)].cb = callback
            self.daemons[(hostname, port)].cbargs = cbargs
        else:
            self.daemons[(hostname, port)] = SocketDaemon(hostname, port, callback, b64, cbargs)

    def start(self):
        if not self.daemons:
            print "SocketController doesn't know where to listen. Use register_address(hostname, port, callback) to register server addresses."
            return
        event.signal(2, event.abort)
        event.dispatch()
