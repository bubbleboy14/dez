from dez.http.errors import HTTPProtocolError

class HTTPRequest(object):
    def __init__(self, conn, router):
        self.__conn = conn
        self.__router = router
        self.headers = {}
        self.__pending = []
        self.__body_started = False
        self.__body_finished = False
        self.__head_finished = False
        self.__conn.set_rmode_delimiter("\r\n\r\n", self._process_head)

    def _process_head(self, data):
        print 'head',data
        self.__head_started = True
        self.action, headers = data.split("\r\n", 1)
        try:
            self.method, self.url, self.protocol = self.action.split(' ',2)
            url_scheme, version = self.protocol.split('/',1)
            self.version_major, self.version_minor = [int(half) for half in version.split('.',1)]
            self.url_scheme = url_scheme.lower()
        except ValueError:
            raise HTTPProtocolError, "Invalid HTTP status line"
        for header in headers.split("\r\n"):
            try:
                key, value = header.split(': ')
            except ValueError:
                raise HTTPProtocolError, "Invalid header:\r\n%s"%header
            self.headers[key.lower()] = value
        self.__content_length = int(self.headers.get('content-length','0'))
        dispatch_cb, args = self.__router(self.url)
        dispatch_cb(self, *args)
#        print 'finished head'
        self.__head_finished = True

    def _process_body(self, data):
        print 'body',data
        if not self.__head_finished or self.__body_finished:
            self.end()
            self.__pending.append(("body",data))
            return self.__next_action()
#        if not self.__head_finished:
#            raise HTTPProcessingError, "body cannot be processed before head"
#        if self.__body_finished:
#            raise HTTPProcessingError, "body already processed"
        self.__body_started = True
        self.__conn.set_rmode_size(self.__content_length, self.__body_cb, data)

    def _process_write(self, data):
        if self.__body_started and not self.__body_finished:
            self.__pending.append(("write",data))
            return self.__next_action()
        self.__body_finished = True
        self.__conn.write(*data)

    def __body_cb(self, data, cb, *args):
        cb(data, *args[0])
        self.__body_finished = True
        self.__next_action()

    def __write_cb(self, cb, args):
        if cb:
            cb(*args)
        self.__next_action()

    def __end_cb(self, cb):
        self.__init__(self.__conn, self.__router)

    def __close_cb(self, cb):
        self.__conn.close(cb)

    def __next_action(self):
        if self.__pending:
            action, data = self.__pending.pop(0)
            getattr(self, "_process_"+action)(data)

    def set_close_cb(self, cb, args):
        self.__conn.set_close_cb(cb, args)

    def read_body(self, cb=None, args=[]):
        self._process_body([cb, args])

    def read_body_stream(self, cb=None, args=[]):
        self.read_body(cb, args)

    def write(self, data, cb=None, args=[], eb=None, ebargs=[]):
        self._process_write([data, self.__write_cb, (cb, args), eb, ebargs])

    def end(self, cb=None):
        self.write("",self.__end_cb,[cb])

    def close(self, cb=None):
        self.write("",self.__close_cb,[cb])

"""
    def write(data, ...)
        if not self.read_body:
            return self.pending_action.append(('write', data, ...))
        self.conn.write(data, ..., ...)
    def read_body(self):
        if self.read_body or self.reading_body:
            raise DontReadTwice
        self.reading_body=True
        self.conn.set_mode_...(...)
    def body_complete(self):
        self.read_body = True
        ...
        for (action, ...) in self.pending_actions:
            if action == 'write':
                self._-write(...)
"""
