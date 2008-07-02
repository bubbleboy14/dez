import event
from dez.http.server import HTTPDaemon, HTTPResponse, RawHTTPResponse

def test_dispatch(request):
    # Very raw way
#    request.write("HTTP/1.0 200 OK\r\nContent-type: text/html\r\nContent-length: 10\r\n\r\nAloha des!", None)
#    request.close()
    
    # HTTPReponse method
    r = HTTPResponse(request)
    r.write('Aloha Des!!')
    r.dispatch()

    # RawHTTPResponse method

#    r = RawHTTPResponse(request)
#    r.write_status(200, "OK")
#    r.write_header("good", "day")
#    r.write_header("Content-length", 10)
#    r.write_headers_end()
#    r.write('Aloha Des!')
#    r.close()


#
    # WSGIHTTPResponse method
    
#def simple_app(environ, start_response):
#    """Simplest possible application object"""
#    status = '200 OK'
#    response_headers = [('Content-type','text/plain')]
#    start_response(status, response_headers)
#    return ['Hello world!\n']
    
#   r = WSGIHTTPResponse(req, simple_app)
#   r.dispatch()

def noop():
    return True

def main(**kwargs):
    httpd = HTTPDaemon(kwargs['domain'], kwargs['port'])
    httpd.register_prefix("/index", test_dispatch)
    event.timeout(1, noop)
    event.dispatch()

def profile(**kwargs):
    import hotshot
    prof = hotshot.Profile("orbited_http_test.profile")
    prof.runcall(main, **kwargs)
    prof.close()
