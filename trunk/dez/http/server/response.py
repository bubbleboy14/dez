try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class HTTPResponse(object):
    id = 0
    def __init__(self, request):
        HTTPResponse.id += 1

        self.id = HTTPResponse.id
        self.request = request
        self.headers = {
            'Content-type': 'text/html'
        }
        self.buffer = []
        self.status = "200 OK"
        self.version_major = 1
        self.version_minor = min(1, request.version_minor)
        if self.version_minor == 1:
            self.headers['Connection'] = 'keep-alive'
            self.headers['Keep-alive'] = '300'

    def __setitem__(self, key, val):
        self.headers[key] = val

    def __getitem__(self, key):
        return self.headers[key]

    def write(self, data):
        self.buffer.append(str(data))

    def dispatch(self, cb=None):
#        print "DISPATCHING:", self.id
        status_line = "HTTP/%s.%s %s\r\n" % (
            self.version_major, self.version_minor, self.status)
        self.headers['Content-length'] = str(sum([len(s) for s in self.buffer]))
        h = "\r\n".join(": ".join((k, v)) for (k, v) in self.headers.items())
        h += "\r\n\r\n"
        response = status_line + h + "".join(self.buffer)
        self.request.write(response, None)
        if self.version_minor == 1 and int(self.headers.get('Keep-alive', '0')) > 0:
#            def cb(*args):
#                print 'ended!'
            self.request.end(cb)#cb)
        else:
#            print 'closing...'
            self.request.close(cb)

class HTTPVariableResponse(object):
    id = 0
    def __init__(self, request):
        HTTPResponse.id += 1
        self.id = HTTPResponse.id
        self.request = request
        self.started = False
        self.headers = {
            'Content-type': 'text/html'
        }
        self.status = "200 OK"
        self.version_major = 1
        self.version_minor = min(1, request.version_minor)
        if self.version_minor == 1:
            self.headers['Connection'] = 'keep-alive'
            self.headers['Keep-alive'] = '300'
            self.headers['Transfer-encoding'] = 'chunked'

    def __setitem__(self, key, val):
        self.headers[key] = val

    def __getitem__(self, key):
        return self.headers[key]

    def write(self, data, cb=None, args=[]):
        if not self.started:
            self.__start_response()
        if not data:
            return
        if self.version_minor == 1:
            self.__write_chunk(data, cb, args)
        else:
            self.request.write(data, cb, args)

    def __write_chunk(self, data, cb=None, args=[]):
        self.request.write("%X\r\n%s\r\n"%(len(data),data))
        if cb:
            cb(*args)

    def __start_response(self, cb=None):
        self.started = True
        status_line = "HTTP/%s.%s %s\r\n" % (
            self.version_major, self.version_minor, self.status)
        h = "\r\n".join(": ".join((k, v)) for (k, v) in self.headers.items())
        h += "\r\n\r\n"
        response = status_line + h
        self.request.write(status_line + h, None)

    def end(self, cb=None):
        if self.version_minor == 1:
            self.__write_chunk("")
            if int(self.headers.get('Keep-alive', '0')) > 0:
                return self.request.end(cb)
        self.request.close(cb)

class RawHTTPResponse(object):
    def __init__(self, request):
        self.request = request
        self.version_major = 1
        self.version_minor = min(1, request.version_minor)

    def write_status(self, code, reason, cb=None, args=[]):
        self.request.write("HTTP/%s.%s %s %s\r\n" % (
            self.version_major, self.version_minor, code, reason), cb, args)

    def write_header(self, key, value, cb=None, args=[]):
        self.request.write('%s: %s\r\n' % (key, value), cb, args)

    def write_headers_end(self, cb=None, args=[]):
        self.request.write('\r\n', cb, args)

    def write(self, data, cb=None, args=[],eb=None, ebargs=[]):
        self.request.write(data, cb, args, eb, ebargs)

    def write_chunk(self, data, cb=None, args=[]):
        self.request.write("%X\r\n%s\r\n"%(len(data),data))
        if len(data) == 0:
            return self.end()
        if cb:
            cb(*args)
    
    def close(self, cb=None):
        self.request.close(cb)

    def end(self, cb=None):
        self.request.end(cb)

class WSGIResponse(object):
    
    def __init__(self, request, app, host=None, port=None):
        self.request = request
        self.app = app
        self.host = host
        self.port = port
        self.response = HTTPResponse(self.request)
        self.environ = {}
        self.stderror = StringIO.StringIO()
        
        self.start_response_called = False
        self.headers_sent = False
        
    def dispatch(self):
#        print 'DEZ: reading body...'
        self.request.read_body(self.body_cb)

    def body_cb(self, body):
        """ response body transmission happens here
            
            Per PEP 333, we ensure that the headers have not already
            been sent. (which is a little silly since we are sending
            the entire response at once)
        """
#        print 'DEZ: Read post body:', body
#        print 'body_cb'
        self.setup_environ(body)
        output = self.app(self.environ, self.start_response)
        output = iter(output)
        
        try:
            first_iteration = output.next()
        except StopIteration:
            first_iteration = ""
        if self.headers_sent:
            raise AssertionError("start_response was not called")
        
        self.response.write(first_iteration)
        for data in output:    
            self.response.write(data)
        self.response.dispatch()

    def start_response(self, status, headers, exc_info=None):
        """ implements start_response per PEP 333
            
            We enforce:
                - if exception info has been sent, then ensure that
                  the headers have not already been sent.
                - start_response has not already been called.
            
        """
        
        if exc_info:
            try:
                if self.headers_sent:
                    raise exc_info[0],exc_info[1],exc_info[2]
            finally:
                exc_info = None
        elif self.start_response_called:
            raise AssertionError("start_response was called twice")
        
#        print 'start_response'
#        print 'status',status
#        print 'headers',headers
        self.response.status = status
        self.response.headers.update(headers)

    def setup_environ(self, body):
#        print 'setup_environ'
        environ = self.environ
        request = self.request
        environ['REMOTE_ADDR'] = self.request.conn.addr # Django fix
        environ['SERVER_NAME'] = self.host
        environ['SERVER_PORT'] = self.port
        environ['REQUEST_METHOD'] = request.method
        path, qs = request.url, ''
        if '?' in request.url:
            path, qs = path.split('?', 1)
#        path_info, script_name = path.rsplit('/', 1)
#        path_info += '/'
#        if request.url != '/favicon.ico':
#            print '==', request.url, path, qs
        environ['SCRIPT_NAME'] = ""#'%s:%s'%(self.host,self.port)
        environ['PATH_INFO'] = path
        environ['QUERY_STRING'] = qs
        content_type = request.headers.get('content-type', None)
        if content_type:
            environ['CONTENT_TYPE'] = content_type
#        content_length = request.headers.get('content-length', None)
#        content_length = len(body)
        environ['CONTENT_LENGTH'] = len(body)
        environ['wsgi.url_scheme']    = 'http'
        environ['wsgi.input']        = StringIO.StringIO(body)
        environ['wsgi.errors']       = self.stderror
        environ['wsgi.version']      = (1,1) # TODO: use version_minor and version_major
        environ['wsgi.multithread']  = False
        environ['wsgi.multiprocess'] = False
        environ['wsgi.run_once']     = False
        for key, val in self.request.headers.items():
            environ['HTTP_%s' % (key.upper().replace('-', '_'),)] = val
            
