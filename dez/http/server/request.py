import event, os
from dez.http.errors import HTTPProtocolError

class HTTPRequest(object):
    id = 0
    def __init__(self, conn):
        HTTPRequest.id += 1
        self.id = HTTPRequest.id
        self.log = conn.get_logger("HTTPRequest(%s)"%(self.id,))
        self.log.debug("__init__")
        self.conn = conn
        self.state = 'action'
        self.headers = {}
        self.case_match_headers = {}
        self.headers_complete = False
        self.write_ended = False
        self.send_close = False
        self.body = None
        self.body_cb = None
        self.body_stream_cb = None
        self.remaining_content = 0
        self.pending_actions = []
        self.set_close_cb(self._onclose, [])

    def process(self):
        self.log.debug("process", self.state)
        return getattr(self, 'state_%s' % (self.state,), lambda : None)()

    def _onclose(self):
        self.write_ended = True

    def set_close_cb(self, cb, args):
        self.conn.set_close_cb(cb, args)
    
    def state_action(self):
        if '\r\n' not in self.conn.buffer:
            return False
        i = self.conn.buffer.find('\r\n')
        self.action = self.conn.buffer.part(0, i)
        try:
            self.method, self.url, self.protocol = self.action.split(' ', 2)
            p, qs = self.url, ""
            if "?" in self.url:
                p, qs = self.url.split("?")
            os.environ.update(PATH_INFO=p, QUERY_STRING=qs)
            url_scheme, version = self.protocol.split('/',1)
            major, minor = version.split('.', 1)
            self.version_major = int(major)
            self.version_minor = int(minor)
            self.url_scheme = url_scheme.lower()
        except ValueError, e:
            self.log.error("state_action", "ValueError", e)
            return self.close_now()
#            raise HTTPProtocolError, "Invalid HTTP status line"
        #self.protocol = self.protocol.lower()
        self.conn.buffer.move(i+2)
        self.state = 'headers'
        self.log.debug("state_action", self.action)
        return self.state_headers()
    
    def state_headers(self):
        while True:
            index = self.conn.buffer.find('\r\n')
            if index == -1:
                return False
            if index == 0:
                self.conn.buffer.move(2)
                self.content_length = int(self.headers.get('content-length', '0'))
                self.headers_complete = True
                self.state = 'waiting'
                self.log.debug("waiting", self.content_length)
                self.conn.route(self)
                return True
            try:
                key, value = self.conn.buffer.part(0, index).split(': ', 1)
            except ValueError, e:
                self.log.debug("state_headers", "ValueError", e)
                return self.close_now()
#                raise HTTPProtocolError, "Invalid HTTP header format"
            self.headers[key.lower()] = value
            self.case_match_headers[key] = key
            self.conn.buffer.move(index+2)

    def state_waiting(self):
        pass

    def read_body(self, cb, args=[]):
        self.log.debug("read_body", self.state, self.content_length)
        self.body_cb = cb, args
        self.state = 'body'
        self.remaining_content = self.content_length
        if self.remaining_content == 0:
            return self.complete()
        self.conn.read_body()
        return self.state_body()

    def read_body_stream(self, stream_cb, args=[]):
        self.remaining_content = self.content_length
        self.body_stream_cb = stream_cb, args
        self.state = 'body'
        self.conn.read_body()
        return self.state_body()

    def state_body(self):
        if self.body_stream_cb:
            bytes_available = min(len(self.conn.buffer), self.remaining_content)
            self.remaining_content -= bytes_available
            cb, args = self.body_stream_cb
            cb(self.conn.buffer.part(0,bytes_available), *args)
            self.conn.buffer.move(bytes_available)
        # Quick hack to fix body bug. TODO: clean up this whole function.
        elif len(self.conn.buffer) >= self.content_length:
            self.remaining_content = 0
        if self.remaining_content == 0:
            return self.complete()

    def complete(self):
        self.log.debug("complete")
        self.conn.complete()
        self.state = 'write'
        if self.body_stream_cb:
            cb, args = self.body_stream_cb
            self.log.debug("firing body_stream callback", str(cb))
            cb("", *args)
        elif self.body_cb:
            cb, args = self.body_cb
            self.log.debug("firing body callback", str(cb))
            d = self.conn.buffer.part(0, self.content_length)
            self.conn.buffer.move(self.content_length)
            if cb:
                cb(d, *args)
        self.state_write()

    def state_write(self):
        self.log.debug("state_write", self.state, self.pending_actions)
        while len(self.pending_actions):
            mode, data, cb, args, eb, ebargs = self.pending_actions.pop(0)
            if mode == "write":
                self.write(data, cb, args, eb, ebargs)
            elif mode == "end":
                self.end(cb, args)
            elif mode == "close":
                self.close(cb, args)

    def write(self, data, cb=None, args=[], eb=None, ebargs=[], override=False):
        self.log.debug("write", self.state, len(data))
        if self.write_ended and not override:
            raise Exception, "end already called"
        if self.state != 'write':
            self.log.debug("state is not 'write'", self.state)
            self.pending_actions.append(("write", data, cb, args, eb, ebargs))
            if self.state == 'waiting':
                self.state = 'body'
            self.log.debug("calling process() from write()")
            return self.process()
        if len(data) == 0:
            return cb and cb(*args)
        self.conn.write(data, self.write_cb, (cb, args), eb, ebargs)

    def write_cb(self, cb=None, args=[]):
        self.log.debug("write_cb", self.write_ended, cb)
        if cb:
            cb(*args)
        if self.write_ended and not self.conn.wevent.pending():
            if self.send_close:
                self.log.debug("closing!!")
                self.state = "closed"
                self.conn.close()
            else:
                self.log.debug("restarting!!")
                self.conn.start_request()

    def end(self, cb=None, args=[]):
        self.log.debug("end", self.write_ended, self.state)
        if self.write_ended:
            return self.log.error("END", "end already called")
        if self.state != "write":
            self.pending_actions.append(("end", None, cb, args, None, None))
            return
        self.state = "ended"
        self.write_ended = True
        self.conn.write("", self.write_cb, (cb, args))

    def close(self, cb=None, args=[]):
        self.log.debug("close", self.write_ended, self.state)
        if self.write_ended:
            return self.log.error("CLOSE", "end already called")
        if self.state != "write":
            return self.pending_actions.append(("close", None, cb, args, None, None))
        self.send_close = True
        self.end(cb, args)

    def close_now(self, reason="hard close"):
        self.conn.close(reason)