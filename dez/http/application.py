import re

from dez.http.server import HTTPDaemon, HTTPResponse, HTTPVariableResponse, WSGIResponse
from dez.http.static import StaticHandler
from dez.http.wsgithreadpool import WSGIThreadPool
from dez.http.proxy.proxy import proxy
from dez.http.errors import HTTPProtocolError

import event
import cgi

class HTTPApplication(object):
    """
        HTTPApplication depends on HTTPDaemon for its prefix ordering behavior.
        It issues cbs as per add_cb_rule in the same manner that HTTPDaemon
        does as well -- it simply passes a dez.http.server.request.HTTPRequest
        instance as the single argument to the callback. Its up to the user to
        construct the appropriate RawHTTPResponse or HTTPResponse as required.
    """

    def __init__(self, bind_address, port, get_logger=None, server_name="Dez", certfile=None, keyfile=None):
        """start listening on the given port (this doesn't include a call to
           event.dispatch)"""
        self.daemon = HTTPDaemon(bind_address, port, get_logger, certfile, keyfile)
        self.host = bind_address
        self.port = port
        self.static_request = StaticHandler(server_name, get_logger)
        self.wsgi_pool = None
        
    def start(self):
        """calls event.dispatch"""
        event.signal(2, self.stop)
        if self.wsgi_pool:
            self.wsgi_pool.start()
        event.dispatch()

    def stop(self):
        if self.wsgi_pool:
            self.wsgi_pool.stop()
        event.abort()
        
    def add_proxy_rule(self, prefix, dest_host, dest_port):
        """ Adds a prefix that will be proxied to the destination
            http_app.add_proxy_rule("/chat/", "127.0.0.1", 4700)
            url == "/chat/index.html"  # will be proxied
            url == "/hello/chat/index.html" # will not be proxied
        """
        self.daemon.register_cb(prefix, self.__proxy, [dest_host, dest_port])

    def __proxy(self, req, host, port):
        return proxy(req, host, port)

    def add_static_rule(self, prefix, local_base_resource):
        """ Adds a prefix that will be served as a static directory or file
            http_app.add_static_rule("/static/", "/home/app/static")
            url == "/static/css/common.css" refers to /home/app/static/css/common.css

            http_app.add_static_rule("/", "/home/app/static/html/index.html")
            url == "/" refers to /home/app/static/html/index.html

            http_app.add_static_rule("/main.html", "/home/app/static/html/main.html")
            url == "/main.html" refers to /home/app/static/html/main.html
            url == "/main.html/foo" returns a 404
        """
        self.daemon.register_cb(prefix, self.static_request, [prefix, local_base_resource])

    def add_cb_rule(self, prefix, cb, parsed=True):
        """ Adds a prefix that will issue a call to cb when a request with that
            url prefix is matched. This works the same as the HTTPDaemon's
            register_prefix function.

            def dispatch(req):
                req.write("HTTP/1.0 200 OK\r\n\r\nHello World")
                req.close()

            http_app.add_cb_rule("/helloworld", dispatch)
        """
        app_cb = cb
        if parsed:
            def format_wrapper(req):
                ParsedHTTPRequest(req, cb)
            app_cb = format_wrapper
        self.daemon.register_cb(prefix, app_cb)

    def add_wsgi_rule(self, prefix, app):
        """ Adds a prefix that will execute (call) a wsgi compliant app function.
            Will provide the app with the appropriate environ and start_response
            function. 
        """
        if not self.wsgi_pool:
            self.wsgi_pool = WSGIThreadPool()
            
        script_name = prefix
        script_name_match = re.match(r"/(\S+?)\/?$", script_name)
        if script_name_match:
            script_name = "/" + script_name_match.group(1)
        
        if script_name != "/":
            try:
                from paste.deploy.config import PrefixMiddleware
                app = PrefixMiddleware(app, prefix=script_name)
            except ImportError:
                message = "could not import PrefixMiddleware from\n"
                message += "paste.deploy.config.\n"
                message += "You must install PasteDeploy before you can"
                message += " load a Pylons application.\n"
                raise ImportError(message)
        
        def wsgi_cb(req):
            r = WSGIResponse(req, app, self.host, self.port)
            self.wsgi_pool.dispatch(r)
#            r.dispatch()
        self.daemon.register_cb(prefix, wsgi_cb)


class ParsedHTTPRequest(object):
    def __init__(self, req, cb):
        self.req = req
        self.cb = cb
        self.form = {}
        self.cookies = {}
        self.qs_params = {}
        req.read_body(self.recv_body)

    def __getattr__(self, key):
        try:
            return object.__getattr__(self, key)
        except AttributeError:
          return getattr(self.req, key)

    def recv_body(self, body):
        self.body = body
        self.dispatch()  

    def dispatch(self):
        self.setup_url()
        self.setup_form()
        self.setup_cookies()
        self.cb(self)

    def setup_url(self):
        if self.req.method.lower() == "get" and "?" in self.req.url:
            self.url, self.qs = self.req.url.split('?', 1)
            for qparam in self.qs.split("&"):
                key, val = qparam.split("=")
                self.qs_params[key] = val
        elif self.req.method.lower() == "post":
            self.url, self.qs = self.req.url, self.body
        else:
            self.url, self.qs = self.req.url, ""

    def setup_form(self):
        try:
            for key, val in cgi.parse_qsl(self.qs):
                self.form[key] = val
        except ValueError:
            raise HTTPProtocolError, "Invalid querystring format"

    def setup_cookies(self):
        pass

def serve_wsgi_application(application, global_conf, **kwargs):
    """ Serve a WSGI application using a paste.deploy.config
    
        This is an adapter to allow dez to be used with the paster
        serve mechanism as interpreted through a *.ini file.
    """
    
    host = kwargs.pop("host", "127.0.0.1")
    port = int(kwargs.pop("port", "8888"))
    
    print "listening on %s:%s" % (host, port)
    httpd = HTTPApplication(host, port, **kwargs)
    httpd.add_wsgi_rule("/", application)
    httpd.start() 
