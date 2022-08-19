from .request import HTTPClientRequest, HTTPClientWriter
from .response import HTTPClientReader
from dez.network import SocketClient
from dez.logging import get_logger_getter
from dez.json import decode, encode
import event

MPBOUND = "53^3n733n"
MPSTART = "--%s"%(MPBOUND,)
MPMID = "\r\n%s\r\n"%(MPSTART,)

SILENT = True

def setSilent(si):
    global SILENT
    SILENT = si

class HTTPClient(object):
    id = 0
    def __init__(self, silent=SILENT):
        HTTPClient.id += 1
        self.id = HTTPClient.id
        self.logger = get_logger_getter("dez")("%s(%s)"%(self.__class__.__name__, self.id)).simple
        self.rcount = 0
        self.client = SocketClient()
        self.silent = silent
        self.requests = {}
        self.log("initialized client")

    def log(self, msg):
        self.silent or self.logger(msg)

    def jayornay(self, txt, json=False):
        if json:
            return decode(txt)
        return txt

    def proc_resp(self, resp, cb=None, json=False):
        return (cb or self.log)(self.jayornay(resp.body.get_value(), json))

    def multipart(self, data):
        bod = []
        for k, v in data.items():
            bod.append('Content-Disposition: form-data; name="%s"\r\n\r\n%s'%(k, v))
        return "%s\r\n%s\r\n%s--\r\n"%(MPSTART, MPMID.join(bod), MPSTART)

    def fetch(self, host, path="/", port=80, secure=False, headers={}, cb=None, timeout=1, json=False):
        url = "%s://%s:%s%s"%(secure and "https" or "http", host, port, path)
        self.log("fetch(%s)"%(url,))
        self.get_url(url, headers=headers, cb=lambda resp : self.proc_resp(resp, cb, json), timeout=timeout)

    def post(self, host, path="/", port=80, secure=False, headers={}, data=None, text=None, cb=None, timeout=1, json=False, multipart=False):
        url = "%s://%s:%s%s"%(secure and "https" or "http", host, port, path)
        self.log("post(%s)"%(url,))
        if data:
            if multipart:
                headers['Content-Type'] = 'multipart/form-data; boundary=%s'%(MPBOUND,)
                headers['Connection'] = 'keep-alive'
                text = self.multipart(data)
            else:
                text = encode(data)
        self.get_url(url, "POST", headers, lambda resp : self.proc_resp(resp, cb, json), body=text, timeout=timeout)

    def get_url(self, url, method='GET', headers={}, cb=None, cbargs=(), eb=None, ebargs=(), body="", timeout=None):
        self.log("get_url: %s"%(url,))
        self.rcount += 1
        path, host, port = self.__parse_url(url)
        self.requests[self.rcount] = URLRequest(self.rcount, path, host, port, method, headers, cb, cbargs, eb, ebargs, body, timeout=timeout)
        self.client.get_connection(host, port, self.__conn_cb, [self.rcount], url.startswith("https://"), self.__conn_timeout_cb, [self.rcount])

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
        ishttps = url.startswith('https://')
        if ishttps:
            url = url[8:]
        elif url.startswith('http://'):
            url = url[7:]
        parts = url.split("/", 1)
        if len(parts) == 1:
            path = "/"
        else:
            path = "/" + parts[1]

        parts = parts[0].split(":", 1)
        if len(parts) == 1:
            port = ishttps and 443 or 80
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
                response.request = self
                self.cb(response, *args)
        
    def failure(self, *args, **kwargs):
        self.failed = True
        if self.eb:
            self.eb(*self.ebargs)
