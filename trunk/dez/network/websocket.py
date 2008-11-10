import optparse
from datetime import datetime
from dez.network.server import SocketDaemon
from dez.network.client import SimpleClient

FRAME_START = chr(0)
FRAME_END   = chr(255)

class WebSocketProxy(object):
    def __init__(self, myhostname, myport, targethostname, targetport, b64=False, verbose=False):
        self.verbose = verbose
        self.target = {'host':targethostname, 'port':targetport, 'b64':b64}
        self.proxy = WebSocketDaemon(myhostname, myport, self._new_conn, b64, self._report)

    def _report(self, data):
        if self.verbose:
            print "%s [WebSocketProxy] %s"%(datetime.now(), data)

    def _new_conn(self, conn):
        self._report("Connecting to TCP server")
        WebSocketProxyConnection(conn, self.target, self._report)

    def start(self):
        self._report("Proxy started")
        self.proxy.start()

class WebSocketProxyConnection(object):
    def __init__(self, client2ws, target, report_cb=lambda x:None):
        self.client2ws = client2ws
        self.report_cb = report_cb
        SimpleClient(target['b64']).connect(target['host'], target['port'], self._conn_server)

    def _conn_server(self, ws2server):
        self.report_cb("TCP connection ready")
        self.ws2server = ws2server
        self.ws2server.set_rmode_close_chunked(self.client2ws.write)
        self.client2ws.set_cb(self.ws2server.write)
        def do_nothing():pass
        def ws2server_close():
            self.report_cb("TCP server disconnected")
            self.report_cb("Closing client connection")
            self.client2ws.set_close_cb(do_nothing)
            self.client2ws.close()
        def client2ws_close():
            self.report_cb("Client disconnected")
            self.report_cb("Closing TCP connection")
            self.ws2server.set_close_cb(do_nothing)
            self.ws2server.close()
        self.ws2server.set_close_cb(ws2server_close)
        self.client2ws.set_close_cb(client2ws_close)
        self.report_cb("Connections linked")

class WebSocketDaemon(SocketDaemon):
    def __init__(self, hostname, port, cb, b64=False, report_cb=lambda x:None):
        SocketDaemon.__init__(self, hostname, port, cb, b64)
        real_cb = self.cb
        def handshake_cb(conn):
            report_cb("Handshake initiated")
            WebSocketHandshake(conn, hostname, port, real_cb, report_cb)
        self.cb = handshake_cb

class WebSocketHandshake(object):
    def __init__(self, conn, hostname, port, cb, report_cb=lambda x:None):
        self.hostname = hostname
        self.port = port
        self.cb = cb
        self.report_cb = report_cb
        self.conn = conn
        self.conn.set_rmode_delimiter('\r\n', self._recv_action)
        self.conn.write("HTTP/1.1 101 Web Socket Protocol Handshake\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\n")

    def _handshake_error(self, data):
        self.report_cb(data)
        self.report_cb("Connection closed")
        self.conn.close()

    def _recv_action(self, data):
        self.report_cb("Processing action line")
        tokens = data.split(' ')
        if len(tokens) != 3:
            return self._handshake_error("Invalid action line")
        self.path = tokens[1]
        self.conn.set_rmode_delimiter('\r\n\r\n', self._recv_headers)

    def _recv_headers(self, data):
        self.report_cb("Processing headers")
        lines = data.split('\r\n')
        self.headers = {}
        for line in lines:
            header = line.split(': ', 1)
            if len(header) != 2:
                return self._handshake_error("Invalid headers")
            self.headers.__setitem__(*header)
        if 'Host' not in self.headers or 'Origin' not in self.headers:
            return self._handshake_error("Missing header")
        self.conn.write("WebSocket-Origin: %s\r\nWebSocket-Location: ws://%s:%s%s\r\n\r\n"%(self.headers['Origin'], self.hostname, self.port, self.path))
        self.report_cb("Handshake complete")
        self.cb(WebSocketConnection(self.conn, self.report_cb))

class WebSocketConnection(object):
    def __init__(self, conn, report_cb=lambda x:None):
        self.conn = conn
        self.conn.halt_read()
        self.report_cb = report_cb
        self.report_cb("Client connection ready")

    def _recv(self, data):
        self.report_cb('Data received:"%s"'%(data))
        if data[0] != FRAME_START:
            self.report_cb("Unframed data received")
            return self.conn.close()
        self.cb(data[1:])

    def set_close_cb(self, cb):
        self.conn.set_close_cb(cb)

    def set_cb(self, cb):
        self.cb = cb
        self.conn.set_rmode_delimiter(FRAME_END, self._recv)

    def write(self, data):
        self.report_cb('Data sent:"%s"'%(data))
        self.conn.write(FRAME_START + data + FRAME_END)

    def close(self):
        self.conn.close()

def startwebsocketproxy():
    parser = optparse.OptionParser('dez_websocket_proxy [DOMAIN] [PORT]')
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    options, args = parser.parse_args()
    try:
        hostname, port = args
    except:
        print '\ndez_websocket_proxy is run with two arguments: the hostname and port of the server being proxied to. For example:\n\ndez_websocket_proxy mydomain.com 5555\n\nwill run a WebSocket server that listens for connections on port 81 and proxies them to a TCP server at mydomain.com:5555.'
        return
    try:
        port = int(port)
    except:
        print '\nThe second argument must be an integer. The command should look like this:\n\ndez_websocket_proxy mydomain.com 5555\n\nTry again!'
        return
    try:
        proxy = WebSocketProxy('localhost', 81, hostname, port, verbose=options.verbose)
    except:
        print '\nPermission denied to use port %s. Depending on how your system is set up, you may need root privileges to run the proxy.'%(port)
        return
    print 'running WebSocket server on port 81'
    print 'proxying to %s:%s'%(hostname, port)
    proxy.start()