from request import HTTPClientRequest, HTTPClientWriter
from response import HTTPClientResponse, HTTPClientReader
from dez.network import SocketClient
from dez.logging import get_logger_getter
import event

class HTTPClient(object):
    def __init__(self):
        self.client = SocketClient()
        self.id = 0
        self.requests = {}
        self.log = get_logger_getter("dez")("HTTPClient").simple
        self.log("initialized client")

    def get_url(self, url, method='GET', headers={}, cb=None, cbargs=(), eb=None, ebargs=(), body="", timeout=None):
        self.log("get_url: %s"%(url,))
        self.id += 1
        path, host, port = self.__parse_url(url)
        self.requests[self.id] = URLRequest(self.id, path, host, port, method, headers, cb, cbargs, eb, ebargs, body, timeout=timeout)
        self.client.get_connection(host, port, self.__conn_cb, [self.id], self.__conn_timeout_cb, [self.id])
    
    def __conn_timeout_cb(self, id):
        self.log("__conn_timeout_cb: %s"%(id,))
        self.requests[id].timeout()
    
    def __conn_cb(self, conn, id):
        self.log("__conn_cb: %s"%(id,))
        writer = HTTPClientWriter(conn)
        request = HTTPClientRequest()
        url_request = self.requests[id]
        request.headers.update(url_request.headers)
        request.method = url_request.method
        request.host = url_request.host
        request.path = url_request.path
        request.port = url_request.port
        request.write(url_request.body)
        writer.dispatch(request, self.__write_request_cb, [id, conn])

    def __write_request_cb(self, id, conn):
        self.log("__write_request_cb: %s"%(id,))
        reader = HTTPClientReader(conn)
        reader.get_full_response(self.__end_body_cb, [id])
#        print "asking for response"

    def __end_body_cb(self, response, id):
#        print "getting response"
#        print response.status_line
#        print response.headers
#        print response.body
        self.log("__end_body_cb: %s"%(id,))
        self.requests[id].success(response)

    def __parse_url(self, url):
        self.log("__parse_url: %s"%(url,))
        """ >>> __hostname_from_url("www.google.com/hello/world?q=yo")
            /, "www.google.com", 80
        """
        if url.startswith('http://'):
            url = url[7:]
        parts = url.split("/", 1)
        if len(parts) == 1:
            path = "/"
        else:
            path = "/" + parts[1]

        parts = parts[0].split(":", 1)
        if len(parts) == 1:
            port = 80
        else:
            port = int(parts[1])
        hostname = parts[0]
        
        return path, hostname, port
        
class URLRequest(object):
    def __init__(self, id, path, host, port, method, headers, cb, cbargs, eb, ebargs, body, timeout=None):
        self.id = id
        self.cb = cb
        self.path = path
        self.host = host
        self.port = port
        self.method = method
        self.headers = headers
        self.cb = cb
        self.cbargs = cbargs
        self.eb = eb
        self.ebargs = ebargs
        self.body = body
        self.timeout = event.event(self.failure)
        if timeout:
            self.timeout.add(timeout)
        self.failed = False
        
    def success(self, response):
        if not self.failed:
            self.timeout.delete()
            if self.cb:
                args = []
                if self.cbargs:
                    args = self.cbargs
                self.cb(response, *args)
        
    def failure(self, *args, **kwargs):
        self.failed = True
        if self.eb:
            self.eb(*self.ebargs)
