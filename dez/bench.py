import rel, time, socket, random
from http import client # for _independent_ pipeline test
from dez.http.client import HTTPClient
from dez.http.errors import HTTPProtocolError

SILENT_CLIENT = True

def ms(bigger, smaller):
    return int(1000*(bigger - smaller))

def display(msg):
    print("   ", msg)

# Piper derived from https://github.com/urllib3/urllib3/issues/52#issuecomment-109756116
class Piper(object):
    def __init__(self, num, get_path, url, validator=None):
        print(" non-dez requests: %s"%(num,))
        self.num = num
        self.count = 0
        self.pipers = []
        self.validator = validator
        for p in range(num):
            self.pipers.append(('GET', get_path()))
        self.conn = client.HTTPConnection(url)
        rel.timeout(0, self.pipe)
        self.start = time.time()
        print("\nInitialized %s (non-dez, standard http) Pipeliners"%(num,))

    def pipe(self): # "unbiased" (non-dez) test ;)
        action, path = self.pipers.pop(0)
        self.conn.request(action, path)
        resp = self.conn.response_class(self.conn.sock, method=self.conn._method)
        self.conn._HTTPConnection__state = 'Idle'
        resp.begin()
        rdata = resp.read()
        self.validator and self.validator(path, rdata, resp.headers)
        assert resp.status == client.OK and rdata
        self.count += 1
        if not self.count % 10:
            print("\nPipelined %s of %s non-dez / standard requests"%(self.count, self.num))
        if self.pipers:
            return True
        print("\nPipelined %s non-dez (standard http lib) requests in %s seconds"%(self.num, time.time() - self.start))

class LoadTester(object):
    def __init__(self, host, port, path, number, concurrency, pipeliners, encrypted=False, validator=None, chunk=100):
        self.host = host
        self.port = port
        self.path = path
        self.number = number
        self.encrypted = encrypted
        self.protocol = encrypted and "https" or "http"
        self.concurrency = concurrency
        self.pipeliners = pipeliners
        self.validator = validator
        self.chunk = chunk
        self.responses = 0
        self.logeach = number < 100
        self.initialize()

    def initialize(self):
        if not self.test():
            return display("no server at %s:%s!\n\ngoodbye\n"%(self.host, self.port))
        display("valid server")
        self.set_url()
        rel.signal(2, self.abort, "Test aborted by user")
        rel.timeout(30, self.abort, "Test aborted after 30 seconds")
        print("\nInitializing Load Tester")
        display("   server url: %s"%(self.url,))
        display("       number: %s"%(self.number,))
        display("  concurrency: %s"%(self.concurrency,))
        self.pipeliners and Piper(self.pipeliners, self.get_path, "%s:%s"%(self.host, self.port), self.validator)
        print("\nBuilding Connection Pool")
        self.t_start = time.time()
        self.client = HTTPClient(SILENT_CLIENT)
        self.client.client.start_connections(self.host, self.port, self.concurrency,
        	self.connections_open, secure=self.encrypted, max_conn=self.concurrency)

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
    	self.url = "%s://%s:%s%s"%(self.protocol, self.host, self.port, self.path)
    	print("\nset url to %s"%(self.url,))

    def get_url(self):
        return self.url

    def get_path(self):
        return self.path

    def connections_open(self):
        self.t_connection = self.t_request = time.time()
        display("pool ready\n\nRunning Test Load")
        display("%s connections opened in %s ms"%(self.concurrency, ms(self.t_connection, self.t_start)))
        display("-")
        for i in range(self.number):
            self.client.get_url(self.get_url(), cb=self.response_cb)

    def response_cb(self, response):
        self.responses += 1
        self.validator and self.validator(response.request.path,
            response.body.get_value(), response.headers)
        if self.responses == self.number:
            now = time.time()
            display("%s responses: %s ms"%(self.responses, ms(now, self.t_request)))
            display("\nRequests Per Second")
            display("%s requests handled in %s ms"%(self.number, ms(now, self.t_connection)))
            display("%s requests per second (without connection time)"%int(self.number / (now - self.t_connection)))
            display("%s requests per second (with connection time)"%int(self.number / (now - self.t_start)))
            self.abort()
        elif self.logeach or not self.responses % self.chunk:
            now = time.time()
            display("%s responses: %s ms"%(self.responses, ms(now, self.t_request)))
            self.t_request = now

class MultiTester(LoadTester):
    def set_url(self):
    	self.url = "%s://%s:%s"%(self.protocol, self.host, self.port)
    	print("\nset url to %s"%(self.url,))

    def get_url(self):
        return "%s%s"%(self.url, self.get_path())

    def get_path(self):
        return random.choice(self.path)