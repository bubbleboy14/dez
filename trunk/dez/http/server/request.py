import event
from dez.http.errors import HTTPProtocolError

class HTTPRequest(object):
    
    def __init__(self, conn):
        self.conn = conn
        self.log = conn.get_logger('HTTPRequest')
        
        self.state = 'action'
        self.headers = {}
        self.case_match_headers = {}
        self.headers_complete = False
        self.complete = False
        self.write_ended = False
        self.send_close = False
        self.body = None
        self.body_cb = None
        self.body_stream_cb = None
        self.remaining_content = 0
        self.write_queue_size = 0
        self.pending_actions = []
            
    def process(self):
        return getattr(self, 'state_%s' % self.state)()        
    
    def set_close_cb(self, cb, args):
        self.conn.set_close_cb(cb, args)
    
    def state_action(self):
        if '\r\n' not in self.conn.buffer:
            return False
        i = self.conn.buffer.find('\r\n')
        self.action = self.conn.buffer.part(0, i)
        try:
            self.method, self.url, self.protocol = self.conn.buffer.part(0, i).split(' ', 2)
        except ValueError:
            raise HTTPProtocolError, "Invalid HTTP status line"
        #self.protocol = self.protocol.lower()
        url_scheme, version = self.protocol.split('/',1)
        major, minor = version.split('.', 1)
        self.version_major = int(major)
        self.version_minor = int(minor)
        self.url_scheme = url_scheme.lower()
        self.conn.buffer.move(i+2)
        self.state = 'headers'
        return self.state_headers()
    
    def state_headers(self):
        while True:
            index = self.conn.buffer.find('\r\n')
            if index == -1:
                return False
            if index == 0:
                self.conn.buffer.move(2)
                self.state = 'headers_completed'
                return self.state_headers_completed()
            try:
                key, value = self.conn.buffer.part(0, index).split(': ', 1)
            except ValueError:
                raise HTTPProtocolError, "Invalid HTTP header format"
            self.headers[key.lower()] = value
            self.case_match_headers[key.lower()] = key
            self.conn.buffer.move(index+2)

    def state_headers_completed(self):
        self.content_length = int(self.headers.get('content-length', '0'))
        self.headers_complete = True
        self.state = 'waiting'

    def state_waiting(self):
        pass

    def read_body(self, cb, args=[]):
        self.body_cb = cb, args
        self.state = 'body'
        self.remaining_content = self.content_length
        if self.remaining_content == 0:
            self.state = "completed"
            return self.state_completed()
        self.conn.read_body()

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
            self.state = 'completed'
            return self.state_completed()

    def state_completed(self):
        if self.body_stream_cb:
            cb, args = self.body_stream_cb
            cb("", *args)
        elif self.body_cb:
            cb, args = self.body_cb
            if cb:
                cb(self.conn.buffer.part(0, self.content_length), *args)
            self.conn.buffer.move(self.content_length)
        if len(self.conn.buffer) > 0:
            b = self.conn.buffer.get_value()
            if b == "\r\n":
                # buffer is line break -- letting it slide
                self.conn.buffer.exhaust()
            else:
                raise HTTPProtocolError, "Unexpected Data: %s" % (repr(b),)

        self.state = 'write'
        for (mode, data, cb, args, eb, ebargs) in self.pending_actions:
            if mode == "write":
                self.write(data, cb, args, eb, ebargs, override=True)
            elif mode == "end":
                self.end(cb)
            elif mode == "close":
                self.close(cb)
                
    def write(self, data, cb=None, args=[],eb=None, ebargs=[],override=False):
        if self.write_ended and not override:
            raise Exception, "end already called"
        if self.state != 'write':
            self.pending_actions.append(("write", data, cb, args, eb, ebargs))
            if self.state == 'waiting':
                self.state = 'body'
                return self.state_body()
            return
        if len(data) == 0:
            return cb()
        self.write_queue_size += 1
        self.conn.write(data , self.write_cb, (cb, args), eb, ebargs)
    
    def write_cb(self, *args):
        self.write_queue_size -= 1
        if self.write_ended and self.write_queue_size == 0:
            if self.send_close:
                self.conn.close()
            else:
                self.conn.start_request()
        if len(args) > 0 and args[0] is not None:
            cb = args[0]
            cbargs = None
            if len(args) > 1:
                cbargs = args[1]
            if cbargs is None:
                cbargs = []
            cb(*cbargs)
            
    def end(self, cb=None, args=[]):
        if self.write_ended:
            raise Exception, "end already called"
        if self.state != "write":
            self.pending_actions.append(("end", None, cb, None, None, None))
            return
        self.write_ended = True
        self.write_queue_size +=1
        self.conn.write("", self.write_cb, (cb,))

    def close(self, cb=None, args=[]):
        if self.write_ended:
            raise Exception, "end already called"
        if self.state != "write":
            self.pending_actions.append(("close", None, cb, None, None, None))
            return
        if not self.write_ended:
            self.end(cb)
        self.send_close = True
    
    def close_now(self, reason="hard close"):
        self.conn.close(reason)
