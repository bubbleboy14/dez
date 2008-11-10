import optparse
from dez.network.server import SocketDaemon
from dez.network.client import SimpleClient

FRAME_START = chr(0)
FRAME_END   = chr(255)

class WebSocketProxy(object):
    def __init__(self, myhostname, myport, targethostname, targetport, b64=False):
        self.target = {'host':targethostname, 'port':targetport, 'b64':b64}
        self.proxy = WebSocketDaemon(myhostname, myport, self._new_conn, b64)

    def _new_conn(self, conn):
        WebSocketProxyConnection(conn, self.target)

    def start(self):
        self.proxy.start()

class WebSocketProxyConnection(object):
    def __init__(self, client2ws, target):
        self.client2ws = client2ws
        c = SimpleClient(target['b64'])
        c.connect(target['host'], target['port'], self._conn_server)

    def _blank_cb(self):
        pass

    def _conn_server(self, ws2server):
        self.ws2server = ws2server
        self.ws2server.set_rmode_close_chunked(self.client2ws.write)
        self.client2ws.set_cb(self.ws2server.write)
        def ws2server_close():
            self.client2ws.set_close_cb(self._blank_cb)
            self.client2ws.close()
        def client2ws_close():
            self.ws2server.set_close_cb(self._blank_cb)
            self.ws2server.close() # what's the problem here?
        self.ws2server.set_close_cb(ws2server_close)
        self.client2ws.set_close_cb(client2ws_close)

class WebSocketDaemon(SocketDaemon):
    def __init__(self, hostname, port, cb, b64=False):
        SocketDaemon.__init__(self, hostname, port, cb, b64)
        real_cb = self.cb
        def handshake_cb(conn):
            WebSocketHandshake(conn, hostname, port, real_cb)
        self.cb = handshake_cb

class WebSocketHandshake(object):
    def __init__(self, conn, hostname, port, cb):
        self.hostname = hostname
        self.port = port
        self.cb = cb
        self.conn = conn
        self.conn.set_rmode_delimiter('\r\n', self._recv_action)
        self.conn.write("HTTP/1.1 101 Web Socket Protocol Handshake\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\n")

    def _recv_action(self, data):
        tokens = data.split(' ')
        if len(tokens) != 3:
            return self.conn.close()
        self.path = tokens[1]
        self.conn.set_rmode_delimiter('\r\n\r\n', self._recv_headers)

    def _recv_headers(self, data):
        lines = data.split('\r\n')
        self.headers = {}
        for line in lines:
            header = line.split(': ', 1)
            if len(header) != 2:
                return self.conn.close()
            self.headers.__setitem__(*header)
        if 'Host' not in self.headers or 'Origin' not in self.headers:
            return self.conn.close()
        self.conn.write("WebSocket-Origin: %s\r\nWebSocket-Location: ws://%s:%s%s\r\n\r\n"%(self.headers['Origin'], self.hostname, self.port, self.path))
        self.cb(WebSocketConnection(self.conn))

class WebSocketConnection(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.halt_read()

    def _recv(self, data):
        if data[0] != FRAME_START:
            return self.conn.close()
        self.cb(data[1:])

    def set_close_cb(self, cb):
        self.conn.set_close_cb(cb)

    def set_cb(self, cb):
        self.cb = cb
        self.conn.set_rmode_delimiter(FRAME_END, self._recv)

    def write(self, data):
        self.conn.write(FRAME_START + data + FRAME_END)

    def close(self):
        self.conn.close()

def startwebsocketproxy():
    parser = optparse.OptionParser('dez_websocket_proxy [DOMAIN] [PORT]')
    try:
        hostname, port = parser.parse_args()[1]
    except:
        print '\ndez_websocket_proxy is run with two arguments: the hostname and port of the server being proxied to. For example:\n\ndez_websocket_proxy mydomain.com 5555\n\nwill run a WebSocket server that listens for connections on port 81 and proxies them to a TCP server at mydomain.com:5555.'
        return
    try:
        port = int(port)
    except:
        print '\nThe second argument must be an integer. The command should look like this:\n\ndez_websocket_proxy mydomain.com 5555\n\nTry again!'
        return
    try:
        proxy = WebSocketProxy('localhost', 81, hostname, port)
    except:
        print '\nPermission denied to use port %s. Depending on how your system is set up, you may need root privileges to run the proxy.'%(port)
        return
    print 'running WebSocket server on port 81'
    print 'proxying to %s:%s'%(hostname, port)
    proxy.start()