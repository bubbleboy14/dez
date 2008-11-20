from dez.buffer import Buffer

class HTTPClientWriter(object):
    def __init__(self, conn):
        self.conn = conn

    def dispatch(self, request, cb, args):
        request.headers['Host'] = self.conn.addr[0]
        self.conn.write(request.render(), self.__request_written_cb, [cb, args])

    def __request_written_cb(self, cb, args):
        return cb(*args)

class HTTPClientRequest(object):
    def __init__(self):
        self.protocol = "HTTP/1.1"
        self.method = "GET"
        self.path = "/"
        self.headers = {}
        self.body = Buffer()

    def write(self, data):
        self.body += data
        self.headers['Content-Length'] = str(len(self.body))

    def render(self):
        output = "%s %s %s\r\n" % (self.method, self.path, self.protocol)
        output += "\r\n".join( [": ".join((key, val)) for (key, val) in self.headers.items() ])
        output += "\r\n\r\n"
        output += self.body.data
        return output

class HTTPClientRawRequest(object):
    def __init__(self):
        self.protocol = "HTTP/1.1"
        self.method = "GET"
        self.path = "/"