from dez.network import SocketClient, SocketDaemon, Connection
import sys

def main2(*args,**kwargs):
    client = SocketClient(cb=LocalEchoHTTPClient)
    client.connect(kwargs['domain'],kwargs['port'])

def delim_period(**kwargs):
    def new_conn(conn):
        EchoConnection(conn, '.')
    server = SocketDaemon(kwargs['domain'], kwargs['port'], new_conn)
    server.start()

def main(**kwargs):
    server = SocketDaemon(kwargs['domain'], kwargs['port'], cb=EchoChunked)
    server.start()

def delim_linebreak(**kwargs):
    server = SocketDaemon(kwargs['domain'], kwargs['port'], cb=EchoConnection)
    server.start()

def http(**kwargs):
    server = SocketDaemon(kwargs['domain'], kwargs['port'], cb=EchoHTTP)
    server.start()

class EchoChunked(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_close_chunked(self._recv)

    def _recv(self, data):
        print 'received:',data
        self.conn.write(data)

class EchoConnection(object):
    def __init__(self, conn, delim='\r\n'):
        self.delim = delim
        self.conn = conn
        self.conn.set_rmode_delimiter(self.delim, self.line_received)

    def line_received(self, data):
        self.conn.write("S: " + data + self.delim)
        print data
        #self.conn.set_rmode_close(self.line_received)

class LocalEchoHTTPClient(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.write("GET / HTTP/1.0\r\nHost: www.google.com\r\n\r\n")
        self.conn.set_rmode_delimiter('\r\n', self.line_received)
        
    def line_received(self, data):
        if data == "": # end of headers
            print "[end of headers]"
            self.conn.set_rmode_close(self.body)
        else:
            print data
            
    def body(self, data):
        print data
        sys.exit(0)

class EchoHTTP(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_delimiter('\r\n\r\n', self.line_received)

    def line_received(self, data):
        self.conn.write("HTTP/1.0 200 OK\r\nContent-Length: 0\r\n\r\n", self.conn.close)

class LengthConnection(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_delimiter('\r\n', self.length_received)

    def length_received(self, data):
        try:
            length = int(data)
        except:
            self.conn.write('Invalid integer: %s'%data, self.close)
        else:
            self.conn.set_rmode_size(length,self.body_received)

    def body_received(self, body):
        self.conn.write('s:%s'%body,self.close)

    def close(self):
        self.conn.close()