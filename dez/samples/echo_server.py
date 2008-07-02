from dez.network import SocketClient, SocketDaemon, Connection
import sys

def main2(*args,**kwargs):
    client = SocketClient(cb=LocalEchoHTTPClient)
    client.connect(kwargs['domain'],kwargs['port'])

def main(**kwargs):
    server = SocketDaemon(kwargs['domain'], kwargs['port'], cb=EchoConnection)
    server.start()

def http(**kwargs):
    server = SocketDaemon(kwargs['domain'], kwargs['port'],cb=EchoHTTP)
    server.start()

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
        sys.exit(0);

class EchoConnection(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_delimiter('\r\n', self.line_received)

    def line_received(self, data):
        #self.conn.write("S: " + data + '\r\n')
        print data
        self.conn.set_rmode_close(self.line_received)

class EchoHTTP(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_delimiter('\r\n\r\n', self.line_received)

    def line_received(self, data):
        print data
        self.conn.set_rmode_close(self.line_received)

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

