from dez.buffer import Buffer
from dez.http.errors import *

class HTTPClientReader(object):
    def __init__(self, conn):
        self.conn = conn
        self.cb_info = (None, None)
        self.mode = "wait"
        self.response = HTTPClientResponse()
        self.helper = HTTPProtocolReader(conn, self.response)

    def get_full_response(self, cb, cbargs):
        self.cb_info = (cb, cbargs)
        self.helper.get_headers(self.__full_headers_end_cb, ())

    def __full_headers_end_cb(self):
#        print "__full_headers_end_cb"
        self.helper.get_body(self.__dispatch_cb, ())

    def get_headers_only(self, cb, cbargs):
        self.cb_info = (cb, cbargs)
        self.helper.get_headers(self.__dispatch_cb, ())

    def __dispatch_cb(self):
#        print "__dispatch_cb"
        cb, args = self.cb_info
        if cb:
            if args is None:
                args = []
            return cb(self.response, *args)

    def get_body(self, cb, cbargs):
        self.cb_info = (cb, cbargs)
        self.helper.get_body(self.__dispatch_cb, ())

    def get_body_stream(self, cb, cbargs):
        self.cb_info = (cb, cbargs)
        self.helper.get_body_stream(self.__dispatch_stream_cb, ())

    def __dispatch_stream_cb(self):
        cb, args = self.cb_info
        if cb:
            if args is None:
                args = []
            return cb(self.response, *args)

class HTTPClientResponse(object):
    def __init__(self):
        self.version_major = None
        self.version_minor = None
        self.status_line = None
        self.status_code = None
        self.status_msg = None
        self.headers = {}
        self.case_match_headers = {}
        self.content_length = None
        self.body = Buffer()
        self.completed = False

class HTTPProtocolReader(object):
    def __init__(self, conn, response):
        self.response = response
        self.conn = conn
        self.cb_info = (None, None)
#        self.body_mode = None
#        self.test_buff = ""

    def get_headers(self, cb, args):
#        print 'get_headers'
        self.cb_info = (cb, args)
#        return self.test_function("")############
        self.conn.set_rmode_delimiter('\r\n', self.__recv_status)

########
#    def test_function(self, data):
#        self.test_buff += data
#        print 'buff: "%s"'%self.test_buff
#        if self.test_buff.endswith("\r\n"):
#            self.__recv_status(self.test_buff[:-2])
#            self.test_buff = ""
#            return
#        self.conn.set_rmode_size(1, self.test_function)
#######

    def __recv_status(self, data):
#        print '__recv_status'
        r = self.response
        r.status_line = data
        try:
            r.protocol, status_code, r.status_msg = data.split(' ',2)
            r.status_code = int(status_code)
        except ValueError:
            raise HTTPProtocolError, "Invalid HTTP status line \"%s\"" % r.status_line
        #self.protocol = self.protocol.lower()
        url_scheme, r.version = r.protocol.split('/',1)
        major, minor = r.version.split('.', 1)
        r.version_major = int(major)
        r.version_minor = int(minor)
        self.conn.set_rmode_delimiter('\r\n', self.__recv_header)

    def __recv_header(self, data):
        if len(data) == 0:
            self.conn.halt_read()
            cb, args, = self.cb_info
            return cb(*args)
        key, val = data.split(': ')
        self.response.case_match_headers[key.lower()] = key
        self.response.headers[key.lower()] = val
        if key.lower() == 'content-length':
            self.response.content_length = int(val)
#            self.response.content_read = 0

    def get_body(self, cb, args):
        if self.response.content_length == 0:
            # return cb("", *args) # this line causes an error
            return cb(*args) # this should work
        self.cb_info = (cb, args)
        # TODO: add transfer-encoding chunked
        if self.response.content_length:
            return self.conn.set_rmode_size(self.response.content_length, self.__recv_body)
        if self.response.version_minor == 0:
            return self.conn.set_rmode_close(self.__recv_body)
        if self.response.headers.get('transfer-encoding', None) == 'chunked':
            return self.conn.set_rmode_delimiter('\r\n', self.__recv_chunk_head)

        raise HTTPProtocolError, "HTTP/1.1 must set content-length or transfer-encoding: chunked"

    def get_body_stream(self, cb, args):
        if self.response.content_length == 0:
            return cb("", *args)
        self.cb_info = (cb, args)
        if self.response.content_length:
            return self.conn.set_rmode_size_chunked(self.response.content_length, self.__recv_body_stream)
        if self.response.version_minor == 0:
            return self.conn.set_rmode_close_chunked(self.__recv_body_stream)
        if self.response.headers.get('transfer-encoding', None) == 'chunked':
            self.conn.set_rmode_delimiter('\r\n', self.__recv_chunk_head, [True])
#    self.conn.set_rmode_delimiter(    

    def __recv_body(self, data):
        # do something with self.response
        self.response.body += data
        self.conn.release()
        cb, args = self.cb_info
        return cb(*args)

    def __recv_chunk_head(self, data, stream=False):
        #stream = False
        i = data.find(';')
        if i == -1:
            size = data
            encodings = ""
        else:
            size = data[:i]
            encodings = data[i+1:]
        chunk_size = int(size, 16) + 2 # Account for trailing \r\n
#        print 'got', size, '(', chunk_size, ') head'
        if stream:
            self.conn.set_rmode_size(chunk_size, self.__recv_chunk_body_stream)
        else:
#            print 'set_rmode_size(', chunk_size, ', self.__recv_chunk_body)'
            self.conn.set_rmode_size(chunk_size, self.__recv_chunk_body)

    def __recv_chunk_body(self, data):
        data = data[:-2] # account for trailing \r\n
#        print 'got', len(data), 'length chunk'
        self.response.body += data
        if len(data) > 0:
            self.conn.set_rmode_delimiter('\r\n', self.__recv_chunk_head)
        else:
#            self.conn.release()
            self.__recv_body("")

    def __recv_chunk_body_stream(self, data):
        data = data[:-2] # account for trailing \r\n
        if len(data) > 0:
            self.conn.set_rmode_delimiter('\r\n', self.__recv_chunk_head, [True])
        self.__recv_body_stream(data)

    def __recv_body_stream(self, data):
        cb, args = self.cb_info
        self.response.body += data
#        if self.response.content_read != None:
#            self.response.content_read += len(data)
        if not len(data):
            #print 'release'
            #self.conn.close()
            self.conn.release()
        return cb(*args)