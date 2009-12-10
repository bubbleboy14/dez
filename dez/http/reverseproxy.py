from dez.network import SocketDaemon, SimpleClient
from datetime import datetime

class ReverseProxyConnection(object):
    def __init__(self, conn, h1, p1, h2, p2, logger, start_data):
        self.front_conn = conn
        self.front_host = h1
        self.front_port = p1
        self.back_host = h2
        self.back_port = p2
        self.logger = logger
        self.log("Initializing connection")
        SimpleClient().connect(h2, p2, self.onConnect, [start_data])

    def log(self, msg):
        self.logger("%s:%s -> %s:%s > %s"%(self.front_host, self.front_port, self.back_host, self.back_port, msg))

    def onConnect(self, conn, start_data):
        self.log("Connection established")
        self.back_conn = conn
        self.front_conn.set_close_cb(self.onClose, [self.back_conn])
        self.back_conn.set_close_cb(self.onClose, [self.front_conn])
        self.front_conn.set_rmode_close_chunked(self.back_conn.write)
        self.back_conn.set_rmode_close_chunked(self.front_conn.write)
        self.back_conn.write(start_data)

    def onClose(self, conn):
        self.log("Connection closed")
        self.front_conn.set_close_cb(None)
        self.back_conn.set_close_cb(None)
        conn.close()
        self.front_conn = None
        self.back_conn = None

class ReverseProxy(object):
    def __init__(self, port, verbose):
        self.port = port
        self.default_address = None
        self.verbose = verbose
        self.domains = {}
        self.daemon = SocketDaemon('', port, self.new_connection)

    def log(self, data):
        if self.verbose:
            print "[%s] %s"%(datetime.now(), data)

    def new_connection(self, conn):
        conn.set_rmode_delimiter('\r\n\r\n', self.route_connection, [conn])

    def route_connection(self, data, conn):
        conn.halt_read()
        domain = None
        for line in data.split('\r\n'):
            if line.startswith('Host: '):
                domain = line[6:]
                if ":" in domain:
                    domain = domain.split(":")[0]
                break
        if not domain:
            return conn.close('no host header')
        self.dispatch(data+'\r\n\r\n', conn, domain)

    def dispatch(self, data, conn, domain):
        if domain in self.domains:
            host, port = self.domains[domain]
        elif self.default_address:
            host, port = self.default_address
        else:
            msg = "unable to route hostname: %s"%(domain,)
            self.log(msg)
            return conn.close(msg)
        ReverseProxyConnection(conn, domain, self.port, host, port, self.log, data)

    def register_default(self, host, port):
        self.default_address = (host, port)

    def register_domain(self, domain, host, port):
        self.domains[domain] = (host, port)

    def start(self):
        self.daemon.start()

def error(msg):
    print "error:",msg
    import sys
    sys.exit(0)

def startreverseproxy():
    import os, optparse
    parser = optparse.OptionParser('dez_reverse_proxy [CONFIG]')
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="log proxy activity")
    parser.add_option("-p", "--port", dest="port", default="80", help="public-facing port (default: 80)")
    options, arguments = parser.parse_args()
    try:
        options.port = int(options.port)
    except:
        error('invalid port specified -- int required')
    if len(arguments) < 1:
        error("no config specified")
    config = arguments[0]
    if not os.path.isfile(config):
        error('no valid config - "%s" not found'%config)
    f = open(config)
    lines = f.readlines()
    f.close()
    try:
        controller = ReverseProxy(options.port, options.verbose)
    except:
        error('could not start server! try running as root!')
    for line in lines:
        line = line.split("#")[0]
        try:
            domain, back_addr = line.split('->')
            domain = domain.strip()
            host, port = back_addr.split(':')
            host = host.strip()
            port = int(port)
        except:
            error('could not parse config. expected "incoming_hostname -> forwarding_address_hostname:forwarding_address_port". failed on line: "%s"'%line)
        if domain == "*":
            print "Setting default forwarding address to %s:%s"%(host, port)
            controller.register_default(host, port)
        else:
            print "Mapping %s to %s:%s"%(domain, host, port)
            controller.register_domain(domain, host, port)
    print "Starting reverse proxy router on port %s"%(options.port)
    controller.start()
