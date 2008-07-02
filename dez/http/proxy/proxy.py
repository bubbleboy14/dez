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
        if request.headers.get('x-requested-with', None) == 'XMLHttpRequest':
            return conn.set_rmode_close(xhr_cb, [request])
        reader = HTTPClientReader(conn)
        reader.get_headers_only(response_headers_cb, [reader, request])
    else:
        conn.write(data) # is this right?

def xhr_cb(data, request):
    request.write(data)
    request.close()

def response_headers_cb(response, reader, request):
    request.write(response.status_line + '\r\n')
    for (key, val) in response.case_match_headers.items():
        request.write('%s: %s\r\n' % (val, response.headers[key]))
    request.write('\r\n')
    reader.get_body_stream(response_body_cb, [ request])

def response_body_cb(response, request):
    data = response.body.get_value()
    if 'content-length' not in response.headers:
        request.write("%X\r\n%s\r\n"%(len(data),data))
    if not len(data):
        return request.end()
    if 'content-length' in response.headers:
        request.write(data)
    response.body.reset()