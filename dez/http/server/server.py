import event
from dez import io
from dez.buffer import Buffer
from dez.logging import default_get_logger
from dez.http.server.router import Router
from dez.http.server.response import RawHTTPResponse, HTTPResponse
from dez.http.server.request import HTTPRequest

class HTTPDaemon(object):
    def __init__(self, host, port, get_logger=None):
        if not get_logger:
            get_logger = default_get_logger
        self.log = get_logger("HTTPDaemon")
        self.get_logger = get_logger
        self.host = host
        self.port = port
        self.log.info("Listening on %s:%s" % (host, port))
        self.sock = io.server_socket(self.port)
        self.listen = event.read(self.sock, self.accept_connection, None, self.sock, None)
        self.router = Router(self.default_cb, [])

    def register_prefix(self, prefix, cb, args=[]):
        self.router.register_prefix(prefix, cb, args)

    def default_404_cb(self, request):
        r = HTTPResponse(request)
        r.status = "404 Not Found"
        r.write("The requested document %s was not found" % request.url)
        r.dispatch()

    def default_200_cb(self, request):
        r = HTTPResponse(request)
        r.status = "200 OK"
        r.dispatch()

    def default_cb(self, request):
        return self.default_404_cb(request)

    def accept_connection(self, ev, sock, event_type, *arg):
        sock, addr = sock.accept()
        HTTPConnection(sock, addr, self.router, self.get_logger)
        return True

class HTTPConnection(object):
    id = 0
    def __init__(self, sock, addr, router, get_logger):
        self.log = get_logger("HTTPConnection")
        self.get_logger = get_logger
        HTTPConnection.id += 1
        self.id = HTTPConnection.id
        self.sock = sock
        self.addr, self.local_port = addr
        self.router = router
        self.response_queue = []
        self.current_cb = None
        self.current_args = None
        self.current_eb = None
        self.current_ebargs = None
        self.wevent = None
        self.revent = None
        self.__close_cb = None
        self.start_request()

    def set_close_cb(self, cb, args):
        self.__close_cb = (cb, args)

    def start_request(self):
        if self.wevent:
            self.wevent.delete()
            self.wevent = None
        if self.revent:
            self.revent.delete()
            self.revent = None
        self.revent = event.read(self.sock, self.read_ready)
        self.request = HTTPRequest(self)
        self.write_buffer = Buffer()
        self.buffer = Buffer()
        self.state = "read"

    def close(self, reason=""):
        if self.__close_cb:
            cb, args = self.__close_cb
            self.__close_cb = None
            cb(*args)
        if self.revent:
            self.revent.delete()
            self.revent = None
        if self.wevent:
            self.wevent.delete()
            self.wevent = None
        self.sock.close()
        if self.current_eb:
            self.current_eb(*self.current_ebargs)
            self.current_eb = None
            self.current_ebargs = None
        while self.response_queue:
            tmp = self.response_queue.pop(0)
            data, self.current_cb, self.current_args, self.current_eb, self.current_ebargs = tmp
            if self.current_eb:
                self.current_eb(*self.current_ebargs)
            self.current_eb = None
            self.current_ebargs = None

    def read_ready(self):
        try:
            data = self.sock.recv(io.BUFFER_SIZE)
            if not data:
                self.close()
                return None
            return self.read(data)
        except io.socket.error:
            self.close()
            return None

    def read_body(self):
        self.revent = event.read(self.sock, self.read_ready)
        self.request.process()

    def read(self, data):
        if self.state != "read":
            self.log.error("Invalid additional data: %s" % data)
            self.close()
        self.buffer += data
        self.request.process()
        if self.request.state == "waiting":
            self.revent.delete()
            self.revent = None
            dispatch_cb, args = self.router(self.request.url)
            dispatch_cb(self.request, *args)
            return None
        elif self.request.state == "completed":
            self.revent.delete()
            self.revent = None
            return None
        return True

    def write(self, data, cb, args,eb=None,ebargs=[]):
        self.response_queue.append((data, cb, args, eb, ebargs))
        if not self.wevent:
            self.wevent = event.write(self.sock, self.write_ready)

    def write_ready(self):
        if self.write_buffer.empty():
            if self.current_cb:
                cb = self.current_cb
                args = self.current_args
                cb(*args)
                self.current_cb = None
            if not self.response_queue:
                self.current_cb = None
                self.current_response = None
                self.wevent = None
                return None
            data, self.current_cb, self.current_args, self.current_eb, self.current_ebargs = self.response_queue.pop(0)
            self.write_buffer.reset(data)
            # call conn.write("", cb) to signify request complete
            if data == "":
                self.wevent = None
                self.current_cb(*self.current_args)
                self.current_cb = None
                self.current_args = None
                self.current_eb = None
                self.current_ebargs = None
                return None
        try:
            bsent = self.sock.send(self.write_buffer.get_value())
            self.write_buffer.move(bsent)
            self.log.debug('write_buffer: return True')
            return True
        except io.socket.error, msg:
            self.log.debug('io.socket.error: %s' % msg)
            self.close(reason=str(msg))
            return None