from dez.network.server import SocketDaemon

FRAME_START = chr(0)
FRAME_END   = chr(255)

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

    def set_cb(self, cb):
        self.cb = cb
        self.conn.set_rmode_delimiter(FRAME_END, self._recv)

    def write(self, data):
        self.conn.write(FRAME_START + data + FRAME_END)