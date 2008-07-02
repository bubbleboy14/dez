from dez.network.server import SocketDaemon
from dez.stomp.server.connection import STOMPConnection
from dez.stomp.server.validator import STOMPValidator

class STOMPServer(object):
    def __init__(self, addr, port):
        self.__val = STOMPValidator()
        self.__server = SocketDaemon(addr, port, self.__connect_cb)
        self.__app_connect_cb = None

    def start(self):
        self.__server.start()

    def set_connect_cb(self, cb):
        self.__app_connect_cb = cb

    def __connect_cb(self, c):
        if self.__app_connect_cb:
            return self.__app_connect_cb(STOMPConnection(c, self.__val))
        print "Application server not available"
