from dez.network import SocketClient, SocketDaemon, Connection
import sys

def main(**kwargs):
    server = SocketDaemon(kwargs['domain'], kwargs['port'], cb=TestCloseChunked)
    server.start()


class TestCloseChunked(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_close_chunked(self.data_received)

    def data_received(self, data):
        print data.replace("\r\n", "\\r\\n\n")


class TestClose(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_close(self.data_received)

    def data_received(self, data):
        print data.replace("\r\n", "\\r\\n\n")


class TestSizeChunked(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_size_chunked(15, self.data_received)

    def data_received(self, data):
        print data.replace("\r\n", "\\r\\n\n")

class TestSize(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_size(15, self.data_received)

    def data_received(self, data):
        print data.replace("\r\n", "\\r\\n\n")


class TestDelimiter(object):
    def __init__(self, conn):
        self.conn = conn
        self.conn.set_rmode_delimiter('\r\n', self.data_received)

    def data_received(self, data):
        print data

#    def close(self):
#        self.conn.close()

