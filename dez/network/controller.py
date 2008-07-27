import event
from dez.network.server import SocketDaemon

class SocketController(object):
    def __init__(self):
        self.daemons = {}

    def register_address(self, hostname, port, callback):
        if (hostname, port) in self.daemons:
            self.daemons[(hostname, port)].cb = callback
        else:
            self.daemons[(hostname, port)] = SocketDaemon(hostname, port, callback)

    def start(self):
        if not self.daemons:
            print "SocketController doesn't know where to listen. Use register_address(hostname, port, callback) to register server addresses."
            return
        event.signal(2, event.abort)
        event.dispatch()