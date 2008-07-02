from dez.http.client import HTTPClientRequest, HTTPClient
import event

def main(**kwargs):
    client = HTTPClient()
    client.get_connection(kwargs['domain'], kwargs['port'], get_conn_cb, [])
    event.dispatch()
    
def get_conn_cb(conn):
    print 'GOT conn', conn
    req = HTTPClientRequest(conn)
#    req.headers['foo'] = 'bar'
#    req.method = 'get'
#    req.write('?baz=foobaz&bar=foobar')
    req.dispatch(response_headers_end_cb, [])


def response_headers_end_cb(response):
    response.read_body(response_completed_cb, [response])

def alternate_response_headers_end_cb(response):
    print 'woot4'
    response.read_body_stream(response_body_stream_cb, [response])

def response_body_stream_cb(chunk, response):
    print chunk

def response_completed_cb(body, response):
    print 'woot5'
    print response.status_line
    print response.headers
    print "#########"
    print "body len:", len(body)
    event.abort()    
