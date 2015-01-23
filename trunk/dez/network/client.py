import event
from dez import io
from dez.network.connection import Connection

class SimpleClient(object):
    def __init__(self, b64=False):
        '''If b64=True, the client reads and writes base64-encoded strings'''
        self.b64 = b64

    def connect(self, host, port, cb, args=[]):
        sock = io.client_socket(host, port)
        self.conn = Connection((host, port), sock, b64=self.b64)
        cb(self.conn, *args)
        event.signal(2, event.abort)
        event.dispatch()

class SocketClient(object):
    def __init__(self):
        self.pools = {}

    def get_connection(self, host, port, cb, args=[], eb=None, ebargs=None, timeout=60, max_conn=5, b64=False):
        addr = host, port
        if addr not in self.pools:
            self.pools[addr] = ConnectionPool(host, port, max_conn, b64)
        self.pools[addr].get_connection(cb, args, timeout)

    def start_connections(self, host, port, num, cb, args=[], timeout=None, max_conn=5):
        addr = host, port
        if addr not in self.pools:
            self.pools[addr] = ConnectionPool(host, port, max_conn)
        self.pools[addr].start_connections(num, cb, args, timeout)

#    def free_connection(self, conn):
#        conn.__start()
#        self.pools[conn.addr].connection_available(conn)

#    def connect(self,hostname,port,cb=None):
#        s = io.client_socket(hostname,port)
#        conn = Connection((hostname,port), s)
#        #TODO pass the callback on to Connection, don't cal it here
#        cb(conn)


class ConnectionPool(object):
    def __init__(self, hostname, port, max_connections=5, b64=False):
        self.addr = hostname, port
        self.connection_count = 0
        self.max_connections = max_connections
        self.b64 = b64

        # real connections
        self.pool = []
#        self.in_use = []

        # requests for connections
        self.wait_index = 0
        self.wait_queue = []
        self.wait_timers = {}
        self.__start_cb_info = None
        self.__start_timer = None
        self.__start_count = None
        
    def start_connections(self, num, cb, args, timeout=None):
        if self.__start_cb_info:
            raise Exception("StartInProgress"), "Only issue one start_connections call in parallel"
        if timeout:
            self.__start_timer = event.timeout(timeout, __start_timeout_cb)
        self.__start_cb_info = (cb, args)
        self.__start_count = num
        for i in range(num):
            self.__start_connection()
        
    def get_connection(self, cb, args, timeout):
        if self.pool:
            c = self.pool.pop()
#            self.in_use.append(c)
            return cb(c,*args)

        if self.connection_count < self.max_connections:
            # make a new connection
#            print 'open a new connection'
            self.__start_connection()

        i = self.wait_index
        timer = event.timeout(timeout, self.__timed_out, i)
        self.wait_timers[i] = cb, args, timer
        self.wait_queue.append(i)
        self.wait_index += 1

        self.__service_queue()

    def __start_connection(self):
            sock = io.client_socket(*self.addr)
            conn = Connection(self.addr, sock, self, self.b64)
            conn.connect()
            self.connection_count += 1

    def connection_available(self, conn):
        self.pool.append(conn)
#        print 'conn available', len(self.pool)
        if self.__start_count and len(self.pool) == self.__start_count:          
            cb, args = self.__start_cb_info
            self.__start_cb_info = None
            if self.__start_timer:
                self.__start_timer.delete()
                self.__start_timer = None
            self.__start_count = None
            cb(*args)
        self.__service_queue()        

    def connection_closed(self, conn):
        if conn in self.pool:
            self.pool.remove(conn)
        self.connection_count -= 1
        if self.wait_queue:
            self.__start_connection()
        self.__service_queue()

    def __timed_out(self, i):
        cb, args, timer = self.wait_timers[i]
        timer.delete()
        del self.wait_timers[i]
        self.wait_queue.remove(i)
        self.connection_count -= 1

    def __service_queue(self):
        if self.pool and self.wait_queue:
            i = self.wait_queue.pop()
            cb, args, timer = self.wait_timers.pop(i)
            timer.delete()
            
            c = self.pool.pop()
#            self.in_use.append(c)
            cb(c, *args)
            
