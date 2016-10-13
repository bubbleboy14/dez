import event, ssl
from dez import io
from dez.buffer import Buffer
from dez.logging import default_get_logger
from dez.http.server.router import Router
from dez.http.server.response import KEEPALIVE, HTTPResponse
from dez.http.server.request import HTTPRequest

class HTTPDaemon(object):
    def __init__(self, host, port, get_logger=default_get_logger, certfile=None):
        self.log = get_logger("HTTPDaemon")
        self.get_logger = get_logger
        self.host = host
        self.port = port
        self.log.info("Listening on %s:%s" % (host, port))
        self.sock = io.server_socket(self.port, certfile)
        self.listen = event.read(self.sock, self.accept_connection, None, self.sock, None)
        self.router = Router(self.default_cb)

    def register_prefix(self, prefix, cb, args=[]):
        self.router.register_prefix(prefix, cb, args)

    def register_cb(self, signature, cb, args=[]):
        self.log.info("Registering callback: %s"%(signature,))
        self.router.register_cb(signature, cb, args)

    def respond(self, request, data=None, status="200 OK"):
        self.log.access("response (%s): '%s', '%s'"%(request.url, status, data))
        r = HTTPResponse(request)
        r.status = status
        if data:
            r.write(data)
        r.dispatch()

    def default_404_cb(self, request):
        self.log.access("404: %s"%(request.url,))
        self.respond(request, "The requested document %s was not found" % (request.url,), "404 Not Found")

    def default_200_cb(self, request):
        self.log.access("200: %s"%(request.url,))
        self.respond(request)

    def default_cb(self, request):
        return self.default_404_cb(request)

    def accept_connection(self, ev, sock, event_type, *arg):
        try:
            sock, addr = sock.accept()
        except ssl.SSLError, e:
            self.log.info("closing connection on SSLError: %s"%(e,))
            return self.sock.close()
        HTTPConnection(sock, addr, self.router, self.get_logger)
        return True

class HTTPConnection(object):
    id = 0
    def __init__(self, sock, addr, router, get_logger):
        HTTPConnection.id += 1
        self.id = HTTPConnection.id
        self.log = get_logger("HTTPConnection(%s)"%(self.id,))
        self.log.debug("__init__")
        self.get_logger = get_logger
        self.sock = sock
        self.addr, self.local_port = addr
        self.router = router
        self.response_queue = []
        self.request = None
        self.current_cb = None
        self.current_args = None
        self.current_eb = None
        self.current_ebargs = None
        self.__close_cb = None
        self._timeout = event.timeout(None, self.timeout)
        self.wevent = event.write(self.sock, self.write_ready)
        self.revent = event.read(self.sock, self.read_ready)
        self.buffer = Buffer()
        self.write_buffer = Buffer()
        self.start_request()

    def set_close_cb(self, cb, args):
        self.__close_cb = (cb, args)

    def start_request(self):
        self.log.debug("start_request", len(self.buffer), len(self.response_queue),
            len(self.write_buffer), self.request and self.request.state or "no request")
        self.log.debug("(deleting wevent; adding revent; new HTTPRequest)")
        self.wevent.pending() and self.wevent.delete()
        self.revent.pending() or self.revent.add()
        self.request = HTTPRequest(self)
        self.state = "read"
        if len(self.buffer):
            self.request.process()
        else:
            self._timeout.add(int(KEEPALIVE))

    def cancelTimeout(self):
        self.log.debug("cancelTimeout (request %s)"%(self.request.id,))
        self._timeout.pending() and self._timeout.delete()

    def timeout(self):
        self.log.debug("TIMEOUT (request %s) -- closing!"%(self.request.id,))
        self.close()

    def close(self, reason=""):
        self.log.debug("close")
        if self.__close_cb:
            cb, args = self.__close_cb
            self.__close_cb = None
            cb(*args)
        self.revent.pending() and self.revent.delete()
        self.wevent.pending() and self.wevent.delete()
        self.sock.close()
        if self.current_eb:
            self.log.debug("triggering current_eb!")
            self.current_eb(*self.current_ebargs)
            self.current_eb = None
            self.current_ebargs = None
        while self.response_queue:
            tmp = self.response_queue.pop(0)
            data, self.current_cb, self.current_args, self.current_eb, self.current_ebargs = tmp
            if self.current_eb:
                self.log.debug("triggering current_eb (response_queue)!")
                self.current_eb(*self.current_ebargs)
            self.current_eb = None
            self.current_ebargs = None

    def read_ready(self):
        self.log.debug("read_ready")
        try:
            data = self.sock.recv(io.BUFFER_SIZE)
            if not data:
                self.log.debug("no data - closing")
                self.close()
                return None
            return self.read(data)
        except io.socket.error, e:
            self.log.debug("read_ready", "io.socket.error", e)
            self.close()
            return None

    def read_body(self):
        self.log.debug("read_body (adding revent)")
        self.revent.pending() or self.revent.add()

    def route(self, request):
        self.log.debug("route", request.id, "[deleting revent, adding wevent]", "[dispatching router]")
        self.revent.pending() and self.revent.delete()
        self.wevent.pending() or self.wevent.add()
        request.state = "write" # questionable
        dispatch_cb, args = self.router(request.url)
        dispatch_cb(request, *args)

    def complete(self):
        self.log.debug("request completed (%s) -- deleting revent, adding wevent"%(self.request.id,))
        self.revent.pending() and self.revent.delete()
        self.wevent.pending() or self.wevent.add()

    def read(self, data):
        self.cancelTimeout()
        self.log.debug("read", self.state)
        if self.state != "read":
            self.log.debug("Invalid additional data: %s" % data)
            self.close()
        self.buffer += data
        self.request.process()
        return self.request.state != "waiting"

    def write(self, data, cb, args=[], eb=None, ebargs=[]):
        self.log.debug("write", len(data))
        self.response_queue.append((data, cb, args, eb, ebargs))
        self.wevent.pending() or self.wevent.add()

    def write_ready(self):
        self.log.debug("write_ready")
        if self.write_buffer.empty():
            if self.current_cb:
                self.log.debug("invoking current_cb", self.current_cb)
                self.current_cb(*self.current_args)
                self.current_cb = None
            if not self.response_queue:
                self.log.debug("no response_queue -- cutting out!")
                self.wevent.pending() and self.wevent.delete()
                return None
            data, self.current_cb, self.current_args, self.current_eb, self.current_ebargs = self.response_queue.pop(0)
            self.write_buffer.reset(data)
            # call conn.write("", cb) to signify request complete
            if data == "":
                self.log.debug("ending request")
                self.wevent.pending() and self.wevent.delete()
                self.current_cb(*self.current_args)
                self.current_cb = None
                self.current_args = None
                self.current_eb = None
                self.current_ebargs = None
                return None
        try:
            self.log.debug("buffer", len(self.write_buffer.get_value()),
                "queue", len(self.response_queue))
            bsent = self.sock.send(self.write_buffer.get_value())
            self.write_buffer.move(bsent)
            return True
        except io.socket.error, msg:
            self.log.debug('io.socket.error: %s' % msg)
            self.close(reason=str(msg))
            return None