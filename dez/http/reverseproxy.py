import json, random
from dez.network import SocketDaemon, SimpleClient
from dez.http.counter import Counter
from dez.http.server import HTTPDaemon
from datetime import datetime
from six import binary_type

class ReverseProxyConnection(object):
    def __init__(self, conn, h1, p1, h2, p2, logger, start_data, counter=None):
        self.front_conn = conn
        self.front_host = h1
        self.front_port = p1
        self.back_host = h2
        self.back_port = p2
        self.logger = logger
        self.log("Initializing connection")
        self.counter = counter or Counter()
        try:
            self.counter.inc("connections", conn.sock)
        except:
            self.front_conn = None
            return self.log("Transport endpoint is not connected - aborting ReverseProxyConnection")
        SimpleClient().connect(h2, p2, self.onConnect, [start_data])

    def log(self, msg):
        self.logger("%s:%s -> %s:%s > %s"%(self.front_host, self.front_port, self.back_host, self.back_port, msg))

    def relay(self, data):
        data = data.replace(b"\r\nHost: ", b"\r\ndrp_ip: %s\r\nHost: "%(self.front_conn.ip.encode(),))
        self.back_conn.write(data)

    def onConnect(self, conn, start_data):
        self.log("Connection established")
        self.back_conn = conn
        self.front_conn.set_close_cb(self.onClose, [self.back_conn])
        self.back_conn.set_close_cb(self.onClose, [self.front_conn])
        self.front_conn.set_rmode_close_chunked(self.relay)
        self.back_conn.set_rmode_close_chunked(self.front_conn.write)
        self.back_conn.write(start_data)

    def onClose(self, conn):
        self.log("Connection closed")
        self.counter.dec("connections")
        self.front_conn.set_close_cb(None)
        self.back_conn.set_close_cb(None)
        self.front_conn.halt_read()
        self.back_conn.halt_read()
        self.front_conn = None
        self.back_conn = None
        conn.soft_close()

BIG_302 = True
BIG_FILES = ["mp3", "png", "jpg", "jpeg", "gif", "pdf", "csv", "mov",
    "zip", "doc", "docx", "jar", "data", "db", "xlsx", "geojson"] # more?

class ReverseProxy(object):
    def __init__(self, port, verbose, redirect=False, protocol="http", certfile=None, keyfile=None, monitor=None):
        self.port = port
        self.default_address = None
        self.verbose = verbose
        self.redirect = redirect
        self.protocol = protocol
        self.domains = {}
        self.counter = Counter()
        self.daemon = SocketDaemon('', port, self.new_connection, certfile=certfile, keyfile=keyfile)
        if monitor:
            self.monitor = HTTPDaemon('', int(monitor))
            self.monitor.register_prefix("/_report", self.report)

    def report(self, req):
        req.write("HTTP/1.0 200 OK\r\n\r\n%s"%(json.dumps(self.counter.report()),))
        req.close()

    def log(self, data):
        if self.verbose:
            print("[%s] %s"%(datetime.now(), data))

    def new_connection(self, conn):
        conn.set_rmode_delimiter('\r\n\r\n', self.route_connection, [conn])

    def _302(self, conn, domain, path): # from hostTrick
        conn.write("HTTP/1.1 302 Found\r\nLocation: %s://%s%s\r\n\r\n"%(self.protocol, domain, path))
        conn.soft_close()

    def domain2hostport(self, domain):
        if domain in self.domains:
            return random.choice(self.domains[domain])
        if self.default_address:
            da = random.choice(self.default_address)
            if da[0] == "auto":
                return (domain, da[1])
            return da
        return None, None

    def cantroute(self, domain, conn):
        msg = "unable to route hostname: %s"%(domain,)
        self.log(msg)
        conn.close(msg)

    def route_connection(self, data, conn):
        conn.halt_read()
        if isinstance(data, binary_type):
            print("reverseproxy closing connection due to illegal bytes in header! data:")
            print(data)
            return self.cantroute("weird bytes!", conn)
        domain = None
        path = None
        should302 = self.redirect
        for line in data.split('\r\n'):
            if line.startswith("GET"):
                path = line.split(" ")[1]
                if "." in path and path.rsplit(".")[1] in BIG_FILES:
                    should302 = True
            elif line.startswith('Host: '):
                domain = line[6:]
                if ":" in domain:
                    domain = domain.split(":")[0]
                break
            elif line.startswith("User-Agent: "):
                self.counter.device(line[12:])
        if not domain:
            return conn.close('no host header')
        self.dispatch(data + '\r\n\r\n', conn, domain, should302, path)

    def dispatch(self, data, conn, domain, should302=False, path=None):
        host, port = self.domain2hostport(domain)
        if not host:
            return self.cantroute(domain, conn)
        if should302 and BIG_302 and host != "localhost":
            self._302(conn, "%s:%s"%(host, port), path)
        else:
            ReverseProxyConnection(conn, domain, self.port, host, port, self.log, data, self.counter)

    def register_default(self, host, port):
        if not self.default_address:
            self.default_address = []
        self.default_address.append((host, port))

    def register_domain(self, domain, host, port):
        if domain not in self.domains:
            self.domains[domain] = []
        self.domains[domain].append((host, port))

    def loud_register(self, domain, host, port):
        if domain == "*":
            self.log("Setting default forwarding address to %s:%s"%(host, port))
            self.register_default(host, port)
        else:
            self.log("Mapping %s to %s:%s"%(domain, host, port))
            self.register_domain(domain, host, port)

    def start(self):
        self.daemon.start()

def error(msg):
    print("error:",msg)
    import sys
    sys.exit(0)

def get_controller(port, verbose, cert, key, monitor):
    if cert and int(port) == 80:
        port = 443
    else:
        try:
            port = int(port)
        except:
            error('invalid port specified -- int required')
    try:
        controller = ReverseProxy(port, verbose, certfile=cert, keyfile=key, monitor=monitor)
    except Exception as e:
        error(verbose and "failed: %s"%(e,) or 'could not start server! try running as root!')
    return controller

def parse_options():
    import optparse
    parser = optparse.OptionParser('dez_reverse_proxy [CONFIG]')
    parser.add_option("-v", "--verbose", action="store_true",
        dest="verbose", default=False, help="log proxy activity")
    parser.add_option("-p", "--port", dest="port", default="80",
        help="public-facing port (default: 80)")
    parser.add_option("-o", "--override_redirect", action="store_true",
        dest="override_redirect", default=False,
        help="prevent 302 redirect of large files (necessary if incoming host matters to target)")
    parser.add_option("-c", "--cert", dest="cert", default=None,
        help="your ssl certificate -- if port is unspecified, uses port 443")
    parser.add_option("-k", "--key", dest="key", default=None,
        help="your ssl key -- if port is unspecified, uses port 443")
    parser.add_option("-s", "--ssl_redirect", dest="ssl_redirect", default=None,
        help="if specified, 302 redirect ALL requests to https (port 443) application at specified host ('auto' leaves host unchanged) - ignores config")
    parser.add_option("-m", "--monitor", dest="monitor", default=None,
        help="listen on specified port for /_report requests (default: None)")
    return parser.parse_args()

def process_targets(domains, controller):
    for domain, targets in list(domains.items()):
        for target in targets:
            host, port = target.split(':')
            controller.loud_register(domain, host, int(port))

def startreverseproxy(options=None, start=True):
    global BIG_302
    import os
    if not options:
        options, arguments = parse_options()    
    BIG_302 = not options.override_redirect
    controller = get_controller(options.port, options.verbose, options.cert, options.key, options.monitor)
    if options.ssl_redirect:
        controller.redirect = True
        controller.protocol = "https"
        print("Redirecting traffic to https (port 443)")
        controller.register_default(options.ssl_redirect, 443)
    else:
        config = getattr(options, "cfg", None) or len(arguments) and arguments[0]
        if not config:
            error("no config specified")
        if not os.path.isfile(config):
            error('no valid config - "%s" not found'%config)
        f = open(config)
        lines = f.readlines()
        f.close()
        try:
            print("checking for JSON config")
            cfg = json.loads("".join([l.strip() for l in lines]))
            print("JSON detected - congratulations!")
            process_targets(cfg["domains"], controller)
        except:
            print("nope! parsing legacy config.")
            for line in lines:
                line = line.split("#")[0]
                if line: # allows comment lines
                    try:
                        domain, back_addr = line.split('->')
                        domain = domain.strip()
                        host, port = back_addr.split(':')
                        host = host.strip()
                        port = int(port)
                    except:
                        error('could not parse config. expected "incoming_hostname -> forwarding_address_hostname:forwarding_address_port". failed on line: "%s"'%line)
                    controller.loud_register(domain, host, port)
    if start:
        print("Starting reverse proxy router on port %s"%(options.port))
        controller.start()