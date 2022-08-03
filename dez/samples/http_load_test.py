import rel, time, socket, random
from optparse import OptionParser
from dez.http.client import HTTPClient
from dez.http.errors import HTTPProtocolError

SILENT_CLIENT = True

class LoadTester(object):
    def __init__(self, host, port, path, number, concurrency, validator=None):
        self.host = host
        self.port = port
        self.path = path
        self.number = number
        self.concurrency = concurrency
        self.validator = validator
        self.responses = 0
        self.initialize()

    def initialize(self):
        if not self.test():
            return display("no server at %s:%s!\n\ngoodbye\n"%(self.host, self.port))
        display("valid server")
        self.set_url()
        rel.signal(2, self.abort, "Test aborted by user")
        rel.timeout(30, self.abort, "Test aborted after 30 seconds")
        print("\nInitializing Load Tester")
        display(" server url: %s"%(self.url,))
        display("     number: %s"%self.number)
        display("concurrency: %s"%self.concurrency)
        print("\nBuilding Connection Pool")
        self.t_start = time.time()
        self.client = HTTPClient(SILENT_CLIENT)
        self.client.client.start_connections(self.host, self.port, self.concurrency, self.connections_open, max_conn=self.concurrency)

    def test(self):
        addr = (self.host, self.port)
        print("\nTesting Server @ %s:%s"%addr)
        test_sock = socket.socket()
        try:
            test_sock.connect(addr)
            test_sock.close()
            return True
        except:
            return False

    def abort(self, msg="goodbye"):
        print("")
        print(msg)
        rel.abort()

    def start(self):
        try:
            rel.dispatch()
        except HTTPProtocolError:
            self.abort("error communicating with server:\nhttp protocol violation")

    def set_url(self):
        self.url = "http://"+self.host+":"+str(self.port)+self.path

    def get_url(self):
        return self.url

    def connections_open(self):
        self.t_connection = self.t_request = time.time()
        display("pool ready\n\nRunning Test Load")
        display("%s connections opened in %s ms"%(self.concurrency, ms(self.t_connection, self.t_start)))
        display("-")
        for i in range(self.number):
            self.client.get_url(self.get_url(), cb=self.response_cb)

    def response_cb(self, response):
        self.responses += 1
        self.validator and self.validator(response.request.path, response.body.get_value())
        if self.responses == self.number:
            now = time.time()
            display("%s responses: %s ms"%(self.responses, ms(now, self.t_request)))
            display("\nRequests Per Second")
            display("%s requests handled in %s ms"%(self.number, ms(now, self.t_connection)))
            display("%s requests per second (without connection time)"%int(self.number / (now - self.t_connection)))
            display("%s requests per second (with connection time)"%int(self.number / (now - self.t_start)))
            self.abort()
        elif not self.responses % 100:
            now = time.time()
            display("%s responses: %s ms"%(self.responses, ms(now, self.t_request)))
            self.t_request = now

class MultiTester(LoadTester):
    def set_url(self):
        self.url = "http://"+self.host+":"+str(self.port)

    def get_url(self):
        return "%s%s"%(self.url, random.choice(self.path))

def ms(bigger, smaller):
    return int(1000*(bigger - smaller))

def display(msg):
    print("   ",msg)

def error(m1, m2):
    print('\n%s\n%s\n\ntry this: "dbench HOSTNAME PORT NUMBER CONCURRENCY"\nor "dbench -h" for help\n'%(m1,m2))

def main():
    parser = OptionParser("dbench HOSTNAME PORT NUMBER CONCURRENCY")
    parser.add_option("-p", "--path", dest="path", default="/", help="path -> http://[DOMAIN]:[PORT][PATH]")
    parser.add_option("-e", "--event", dest="event", default="epoll", help="change event delivery system (options: pyevent, epoll, poll, select) default: epoll")
    ops, args = parser.parse_args()
    if len(args) < 4:
        return error("insufficient arguments specified", "dbench requires 4 arguments")
    hostname = args[0]
    try:
        port = int(args[1])
        number = int(args[2])
        concurrency = int(args[3])
    except:
        return error("invalid argument","PORT, NUMBER, and CONCURRENCY must all be integers")
    print("\nLoading Event Listener")
    display(" requesting: %s"%ops.event)
    e = rel.initialize([ops.event])
    if e != ops.event:
        display("failed to load %s!"%ops.event)
    display("     loaded: %s"%e)
    LoadTester(hostname, port, ops.path, number, concurrency).start()