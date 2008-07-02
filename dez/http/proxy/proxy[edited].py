from dez.network.client import SocketClient
from dez.http.client.response import HTTPClientReader

client = SocketClient()

def proxy(request, dest_host, dest_port):
    client.get_connection(dest_host, dest_port, connection_cb, [request])

def connection_cb(conn, request):
    conn.write(request.action + '\r\n')
    for (key, val) in request.headers.items():
        conn.write('%s: %s\r\n' % (key, val))
    conn.write('\r\n')
    request.read_body_stream(body_cb, [conn, request])

def body_cb(data, conn, request):
    if not data:
        reader = HTTPClientReader(conn)
        reader.get_headers_only(response_headers_cb, [reader, request])
    else:
        conn.write(data)

def response_headers_cb(response, reader, request):
    request.write(response.status_line + '\r\n')
    for (key, val) in response.case_match_headers.items():
        request.write('%s: %s\r\n' % (val, response.headers[key]))
    request.write('\r\n')
    reader.get_body_stream(response_body_cb, [request])

def response_body_cb(response, request):
    data = response.body.get_value()
    if not response.content_length:#'content-length' not in response.headers:
        data = "%X\r\n%s\r\n"%(len(data),data)
    request.write(data)
    print 'content_read:',response.content_read
    print 'content_length:',response.content_length
    if not data or data == "0\r\n\r\n" or response.content_length and response.content_length == response.content_read:
        print '\r\ndata = "%s"\r\n'%data
        #print 'release'
        #request.close()
        request.process()
    response.body.reset()
