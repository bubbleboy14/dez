import rel, time
rel.override()
from dez.http.client import HTTPClient
from optparse import OptionParser

class LoadTester(object):
    def __init__(self, host, port, location, number, concurrency):
        self.url = "http://"+host+":"+port+location
        self.number = number
        self.concurrency = concurrency
        print "       server url:",self.url
        print "           number:",self.number
        print "      concurrency:",self.concurrency
        self.client = HTTPClient()
        self.client.client.start_connections(host, int(port), self.concurrency, self.connections_open, max_conn=concurrency)
        self.time_start = time.time()
        self.responses = 0

    def connections_open(self):
        self.time_request_start = self.time_request = time.time()
        print ""
        print "Running Load Test"
        print "   ", self.concurrency, 'connections opened in', int(1000*(self.time_request_start - self.time_start)), "ms"
        print "    -"
        for i in range(self.number):
            self.client.get_url(self.url, cb=self.response_cb, cbargs=[i+1])

    def response_cb(self, response, i):
        self.responses += 1
        if self.responses == self.number:
            now = time.time()
            print "   ", self.responses, 'responses:', int(1000*(now - self.time_request)), "ms"
            print "    -"
            print ""
            print "Requests Per Second"
            print "   ", self.number, 'requests handled in', int(1000*(now - self.time_request_start)), "ms"
            print "   ", int(self.number / (now - self.time_start)), "requests per second (with connection time)"
            print "   ", int(self.number / (now - self.time_request_start)), "request per second (without connection time)"
            return rel.abort()
        if not self.responses % 100:
            now = time.time()
            print "   ", self.responses, 'responses:', int(1000*(now - self.time_request))
            self.time_request = now

def parse_input():
    parser = OptionParser()
    parser.add_option("-d", "--domain", dest="domain", default="localhost", help="test server at DOMAIN")
    parser.add_option("-p", "--port", dest="port", default="80", help="test server at PORT")
    parser.add_option("-l", "--location", dest="location", default="/", help="path -> http:// DOMAIN : PORT LOCATION")
    parser.add_option("-n", "--number", dest="number", default="1000", help="total NUMBER of connections")
    parser.add_option("-c", "--concurrency", dest="concurrency", default="100", help="connection CONCURRENCY")
    return parser.parse_args()

def main():
    ops, args = parse_input()
    if not args:
        args = ["pyevent"]
    print ""
    print "Initializing Load Tester"
    print "   event listener:",rel.initialize(args)
    rel.signal(2, rel.abort)
    rel.timeout(30, rel.abort)
    l = LoadTester(ops.domain, ops.port, ops.location, int(ops.number), int(ops.concurrency))
    rel.dispatch()