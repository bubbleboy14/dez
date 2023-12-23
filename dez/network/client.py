import event
from dez import io
from dez.network.connection import Connection

SILENT = True
MIN_CONN = 10
MAX_CONN = 1000

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

    def get_connection(self, host, port, cb, args=[], secure=False, eb=None, ebargs=None, timeout=60, max_conn=MAX_CONN, b64=False):
        addr = host, port
        if addr not in self.pools:
            self.pools[addr] = ConnectionPool(host, port, secure, max_conn, b64)
            MIN_CONN and self.pools[addr].spawn(MIN_CONN)
        self.pools[addr].get_connection(cb, args, timeout)

    def start_connections(self, host, port, num, cb, args=[], secure=False, timeout=None, max_conn=MAX_CONN):
        addr = host, port
        if addr not in self.pools:
            self.pools[addr] = ConnectionPool(host, port, secure, max_conn)
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
    def __init__(self, hostname, port, secure=False, max_connections=MAX_CONN, b64=False):
        self.addr = hostname, port
        self.hostname = hostname
        self.port = port
        self.secure = secure
        self.connection_count = 0
        self.max_connections = max_connections
        self.b64 = b64

        # real connections
        self.pool = []

        # requests for connections
        self.wait_index = 0
        self.wait_queue = []
        self.wait_timers = {}
        self.__start_cb_info = None
        self.__start_timer = None
        self.__start_count = None
        
    def log(self, *msg):
        SILENT or print(*msg)

    def stats(self, msg):
        self.log(msg, len(self.wait_queue), "queue;", len(self.pool),
            "pool", self.connection_count, "conns", self.wait_index, "reqs")

    def start_connections(self, num, cb, args, timeout=None):
        if self.__start_cb_info:
            raise Exception("StartInProgress")("Only issue one start_connections call in parallel")
        if timeout:
            self.__start_timer = event.timeout(timeout, __start_timeout_cb)
        self.__start_cb_info = (cb, args)
        self.__start_count = num
        self.spawn(num)

    def get_connection(self, cb, args, timeout):
        self.stats("GET CONN")
        i = self.wait_index
        timer = event.timeout(timeout, self.__timed_out, i)
        self.wait_timers[i] = cb, args, timer
        self.wait_queue.append(i)
        self.wait_index += 1
        self._churn()

    def _churn(self):
        self.stats("CHURN")
        if self.pool:
            self.__service_queue()
        elif self.connection_count < self.max_connections:
            self.__start_connection()

    def spawn(self, num):
        self.stats("STARTING %s CONNS"%(num,))
        for i in range(num):
            self.__start_connection()

    def __start_connection(self):
        sock = io.client_socket(self.hostname, self.port, self.secure)
        Connection(self.addr, sock, self, self.b64).connect()
        self.connection_count += 1

    def connection_available(self, conn):
        self.pool.append(conn)
        self.stats("CONN AVAILABLE")
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
        self.stats("CONN CLOSED")
        self.wait_queue and self._churn()

    def __timed_out(self, i):
        cb, args, timer = self.wait_timers[i]
        timer.delete()
        del self.wait_timers[i]
        self.wait_queue.remove(i)
        self.connection_count -= 1
        self.stats("TIMEOUT")

    def __service_queue(self):
        self.stats("SERVICE")
        while self.pool and self.wait_queue:
            i = self.wait_queue.pop(0)
            cb, args, timer = self.wait_timers.pop(i)
            timer.delete()
            cb(self.pool.pop(0), *args)
        if self.wait_queue and self.connection_count < self.max_connections:
            self.spawn(min(len(self.wait_queue),
                self.max_connections - self.connection_count))