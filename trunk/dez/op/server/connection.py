import urllib
from dez.buffer import Buffer
from dez.op.server.frame import Frame, SendFrame
from dez.http.client import HTTPClient

#DELIM = "^@\r\n"
DELIM = "\x00"

class Callback_Handler(object):
    def __init__(self, writer):
        self.writer = writer
        self.http = HTTPClient()
        self.cbs = {
            "signon":(False, None),
            "signoff":(False, None),
            "failure":(False, None),
            "success":(False, None),
            "message":(False, None)
        }

    def set_url(self, func, url):
        if func in self.cbs:
            self.cbs[func] = (True, url)
            return True
        return False

    def dispatch(self, func, headers, cb=None, cbarg=()):
        active, url = self.cbs[func]
        if active:
            headers["function"] = func
            if not url:
                return self.writer("CALLBACK", headers, "", cb, cbarg)
            final_headers = []
            for key in headers:
                if key == 'recipients':
                    for recipient in headers['recipients']:
                        final_headers.append(('recipient', recipient))
                else:
                    final_headers.append((key, headers[key]))
            self.http.get_url(url, "POST", {}, cb, cbarg, body=urllib.urlencode(final_headers))

class OPConnection(object):
    id = 0
    def __init__(self, conn, validator):
        OPConnection.id += 1
        self.id = OPConnection.id
        self.conn = conn
        self.validator = validator
        self.ids = set()
        self.app_cb = self.__default_app_cb
        self.app_args = []
        self.callbacks = Callback_Handler(self.write)
        self.conn.set_rmode_delimiter(DELIM, self.__connect)

    def __default_app_cb(self, req):
        print "no application callback specified"

    def set_request_cb(self, cb, args=()):
        self.app_cb = cb
        self.app_args = args

    def signon_cb(self, key, cb=None, cbarg=()):
        self.callback("signon",{"key":key},cb,cbarg)

    def signoff_cb(self, key, reason="", failed_msgs={}, cb=None, cbarg=()):
        headers = {"key":key}
        if reason:
            headers['reason'] = reason
        failed = ""
        for item in failed_msgs:
            failed += key + ":" + failed_msgs[item] + "|"
        if failed:
            headers["failed_msgs"] = failed[:-1]
        self.callback("signoff",headers,cb,cbarg)

    def message_cb(self, key, msg, cb=None, cbarg=()):
        self.callback("message",{"key":key,"msg":msg},cb,cbarg)

    def callback(self, func, headers, cb=None, cbarg=()):
        self.callbacks.dispatch(func, headers, cb, cbarg)

    def set_close_cb(self, cb, args=()):
        self.conn.set_close_cb(cb, args)

    def __parse_headers(self, headers):
        s = ""
        for key, val in headers.items():
            if key == "recipients":
                for r in val:
                    s += "recipient:"+str(r)+"\r\n"
            else:
                s += key+":"+val+"\r\n"
        return s

    def __connect(self, data):
        req = Frame(self, Buffer(data, mode="consume"))
        if self.validator(req):
            if req.action != "CONNECT":
                return req.error("'CONNECT' not sent")
            self.response = req.headers.get("response","none")
            self.__forward(req)
            self.conn.set_rmode_delimiter(DELIM, self.__process)

    def __process(self, data):
        req = Frame(self, Buffer(data, mode="consume"))
        if req.action == "CONNECT":
            return req.error("'CONNECT' already sent")
        if self.validator(req):
            self.__forward(req)

    def __forward(self, req):
        if req.request_id in self.ids:
            return req.error("non-unique 'id':%s"%req.request_id)
        self.ids.add(req.request_id)
        if "response" not in req.headers:
            req.headers["response"] = self.response
        if self.__final_check(req):
            self.app_cb(req)

    def __final_check(self, req):
        if req.action == "SEND":
            req.__class__ = SendFrame
        elif req.action == "CALLBACK":
            if not self.callbacks.set_url(req.headers['function'],req.headers.get('url',None)):
                req.error("Invalid function specified. Legitimate functions: signon, signoff, failure, success, message.")
                return False
        return True

    def write(self, action, headers, body, cb, cbarg):
        s = action+"\r\n"
        s += self.__parse_headers(headers)
        s += "\r\n"+body+DELIM
        self.conn.write(s, cb, cbarg)

    def close(self):
        self.conn.close()
