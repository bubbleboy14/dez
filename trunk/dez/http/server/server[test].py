from dez.network.server import SocketDaemon
from dez.http.server.router import Router
from dez.http.server.response import HTTPResponse
from request import HTTPRequest

class HTTPDaemon(object):
    def __init__(self, host, port, get_logger=None):
        self.__server = SocketDaemon(host, port, self.__new_connection)
        self.router = Router(self.__404, [])

    def __new_connection(self, conn):
        HTTPRequest(conn, self.router)

    def __404(self, request):
        r = HTTPResponse(request)
        r.status = "404 Not Found"
        r.write("The requested document %s was not found" % request.url)
        r.dispatch()

    def start(self):
        self.__server.start()

    def register_prefix(self, prefix, cb, args=[]):
        self.router.register_prefix(prefix, cb, args)
