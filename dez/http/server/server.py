import event
from dez import io
from dez.buffer import Buffer
from dez.logging import default_get_logger
from dez.http.counter import Counter
from dez.http.server.router import Router
from dez.http.server.response import KEEPALIVE, HTTPResponse
from dez.http.server.request import HTTPRequest

class HTTPDaemon(object):
    def __init__(self, host, port, get_logger=default_get_logger, certfile=None, keyfile=None, cacerts=None, rollz={}, whitelist=[]):
        self.log = get_logger("HTTPDaemon")
        self.get_logger = get_logger
        self.host = host
        self.port = port
        self.secure = bool(certfile)
        self.counter = Counter()
        self.log.info("Listening on %s:%s" % (host, port))
        self.sock = io.server_socket(self.port, certfile, keyfile, cacerts)
        self.listen = event.read(self.sock, self.accept_connection, None, self.sock, None)
        self.router = Router(self.default_cb, roll_cb=self.roll_cb, rollz=rollz, get_logger=get_logger, whitelist=whitelist)

    def register_prefix(self, prefix, cb, args=[]):
        self.router.register_prefix(prefix, cb, args)

    def register_cb(self, signature, cb, args=[]):
        self.log.info("Registering callback: %s"%(signature,))
        self.router.register_cb(signature, cb, args)

    def respond(self, request, data=None, status="200 OK", headers={}):
        self.log.access("response (%s): '%s', '%s'"%(request.url, status, data))
        r = HTTPResponse(request)
        r.status = status
        for k, v in list(headers.items()):
            r.headers[k] = v
        if data:
            r.write(data)
        r.dispatch()

    def roll_cb(self, request):
        self.log.info("302 (rolled!): %s"%(request.url,))
        self.counter.roll()
        self.respond(request, "rolled!", "302 Found",
            { "Location": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" })

    def default_404_cb(self, request):
        self.log.access("404: %s"%(request.url,))
        self.respond(request, "The requested document %s was not found" % (request.url,), "404 Not Found")

    def default_200_cb(self, request):
        self.log.access("200: %s"%(request.url,))
        self.respond(request)

    def default_cb(self, request):
        return self.default_404_cb(request)

    def handshake_cb(self, sock, addr):
        def cb():
            HTTPConnection(sock, addr, self.router, self.get_logger, self.counter)
        return cb

    def accept_connection(self, ev, sock, event_type, *arg):
        self.log.debug("accept_connection")
        try:
            sock, addr = sock.accept()
            if self.secure:
                io.ssl_handshake(sock, self.handshake_cb(sock, addr))
            else:
                HTTPConnection(sock, addr, self.router, self.get_logger, self.counter)
        except io.socket.error as e:
            self.log.info("abandoning connection on socket error: %s"%(e,))
        return True

class HTTPConnection(object):
    id = 0
    def __init__(self, sock, addr, router, get_logger, counter=None):
        HTTPConnection.id += 1
        self.id = HTTPConnection.id
        self.log = get_logger("HTTPConnection(%s)"%(self.id,))
        self.log.debug("__init__")
        self.get_logger = get_logger
        self.sock = sock
        self.ip = sock.getpeername()[0]
        self.real_ip = self.ip # subject to later modification based on request headers
        self.addr, self.local_port = addr
        self.router = router
        self.counter = counter or Counter()
        self.counter.inc("connections", sock)
        self.response_queue = []
        self.fried = False
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
        self.counter.inc("requests")
        self.wevent.pending() and self.wevent.delete()
        self.revent.pending() or self.revent.add()
        self.request and self.request.dereference()
        self.request = HTTPRequest(self)
        if len(self.buffer):
            self.request.process()
        else:
            self._timeout.add(KEEPALIVE)

    def cancelTimeout(self, hard=False):
        self.log.debug("cancelTimeout (request %s)"%(self.request.id,))
        self._timeout.pending() and self._timeout.delete(hard)

    def timeout(self):
        self.log.debug("TIMEOUT (request %s) -- closing!"%(self.request.id,))
        self.close()

    def fry(self, reason=""):
        self.log.debug("fried", reason)
        self.fried = True
        self.close(reason)

    def close(self, reason=""):
        self.log.debug("close", reason)
        if not self.fried:
            if len(self.write_buffer) or len(self.response_queue):
                self.log.error("ALERT! attempting close() w/ %s write_buffer!"%(len(self.write_buffer)),)
                if self.request.write_ended:
                    self.log.error("write ended! unending.")
                    self.request.write_ended = False
                if self.request.send_close:
                    self.log.error("send close! unsendclosing.")
                    self.request.send_close = False
                if not self.wevent.pending():
                    self.log.error("wevent not pending! adding.")
                    self.wevent.add()
                return
            if len(self.buffer):
                self.log.error("close", "buffer present - starting new request")
                return self.start_request()
            if not self.revent.pending():
                self.log.debug("close", "revent not pending - starting new request")
                return self.start_request()
        self.cancelTimeout(True)
        self.counter.dec("connections")
        if self.__close_cb:
            self.log.debug("close - triggering __close_cb!")
            cb, args = self.__close_cb
            self.__close_cb = None
            cb(*args)
        self.request.dereference()
        self.revent.dereference()
        self.wevent.dereference()
        self.sock.close()
        if self.current_eb:
            self.log.error("close - triggering current_eb!")
            self.current_eb(*self.current_ebargs)
            self.current_eb = None
            self.current_ebargs = None
        while self.response_queue:
            tmp = self.response_queue.pop(0)
            data, self.current_cb, self.current_args, self.current_eb, self.current_ebargs = tmp
            if self.current_eb:
                self.log.error("close - triggering current_eb (response_queue)!")
                self.current_eb(*self.current_ebargs)
            self.current_eb = None
            self.current_ebargs = None
        self.request = None
        self.buffer = None
        self.write_buffer = None
        self.log = None
        self._timeout = None
        self.__close_cb = None

    def read_ready(self):
        self.log.debug("read_ready")
        try:
            data = self.sock.recv(io.BUFFER_SIZE)
            if not data:
                self.log.debug("no data - closing")
                self.request.close(hard=True)
                return None
            return self.read(data)
        except io.ssl.SSLError as e: # not SSLWantReadError for python 2.7.6
            self.log.debug("read_ready (waiting)", "SSLError", e)
            return True # wait
        except io.socket.error as e:
            self.fry("read_ready (closing): io.socket.error - %s"%(e,))
            return None

    def read_body(self):
        self.log.debug("read_body (adding revent)")
        self.revent.pending() or self.revent.add()

    def route(self, request):
        self.log.debug("route", request.id, "[deleting revent, adding wevent]", "[dispatching router]")
        self.counter.device(request.headers.get("user-agent", "none"))
        self.revent.pending() and self.revent.delete()
        self.wevent.pending() or self.wevent.add()
        request.state = "write" # questionable
        dispatch_cb, args = self.router(request)
        dispatch_cb(request, *args)

    def complete(self):
        self.log.debug("request completed (%s) -- deleting revent, adding wevent"%(self.request.id,))
        self.revent.pending() and self.revent.delete()
        self.wevent.pending() or self.wevent.add()

    def read(self, data):
        self.cancelTimeout()
        self.log.debug("read", self.request.state, len(data))
        if self.request.state == "write":
            self.log.error("Invalid additional data: %s" % data)
            return self.request.close(hard=True)
        self.buffer += data
        self.request.process()
        return self.request and self.request.state != "waiting"

    def write(self, data, cb, args=[], eb=None, ebargs=[]):
        if not self.log:
            print("connection closed - can't write", len(data))
            return self.wevent.pending() and self.wevent.delete()
        self.log.debug("write", len(data))
        self.response_queue.append((data, cb, args, eb, ebargs))
        self.wevent.pending() or self.wevent.add()

    def write_ready(self):
        self.log.debug("write_ready")
        if self.write_buffer.empty():
            if self.current_cb:
                self.log.debug("write_ready", "invoking current_cb", self.current_cb)
                self.current_cb(*self.current_args)
                self.current_cb = None
            if not self.response_queue:
                self.log.debug("write_ready", "buffer present")
                if len(self.buffer):
                    if self.revent.pending():
                        self.log.debug("write_ready", "revent pending - doing nothing")
                    else:
                        self.log.debug("write_ready", "revent not pending - starting new request")
                        self.start_request()
                else:
                    self.log.debug("no response_queue or buffer -- cutting out!")
                    self.wevent.pending() and self.wevent.delete()
                return None
            data, self.current_cb, self.current_args, self.current_eb, self.current_ebargs = self.response_queue.pop(0)
            self.write_buffer.reset(data)
            # call conn.write("", cb) to signify request complete
            if not data:
                self.log.debug("write_ready", "no data")
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
            self.write_buffer.send(self.sock)
            return True
        except io.socket.error as msg:
            self.fry('io.socket.error: %s' % msg)
            return None