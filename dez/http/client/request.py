from dez.buffer import WriteBuffer

class HTTPClientWriter(object):
    def __init__(self, conn, silent=True):
        self.conn = conn
        self.silent = silent

    def log(self, *msg):
        self.silent or print("HTTPClientWriter", *msg)

    def dispatch(self, request, cb, args):
        self.log("dispatch!")
        request.headers['Host'] = self.conn.addr[0]
        self.conn.write(request.render(), self.__request_written_cb, [cb, args])

    def __request_written_cb(self, cb, args):
        self.log("__request_written_cb")
        return cb(*args)

class HTTPClientRequest(object):
    def __init__(self, silent=True):
        self.protocol = "HTTP/1.1"
        self.silent = silent
        self.method = "GET"
        self.path = "/"
        self.headers = {}
        self.body = WriteBuffer()

    def log(self, *msg):
        self.silent or print("HTTPClientRequest", *msg)

    def write(self, data):
        self.log("write", data)
        self.body += data
        self.headers['Content-Length'] = str(len(self.body))

    def render(self):
        output = "%s %s %s\r\n" % (self.method, self.path, self.protocol)
        output += "\r\n".join( [": ".join((key, val)) for (key, val) in list(self.headers.items()) ])
        output += "\r\n\r\n"
        return output.encode() + self.body.data

class HTTPClientRawRequest(object):
    def __init__(self):
        self.protocol = "HTTP/1.1"
        self.method = "GET"
        self.path = "/"