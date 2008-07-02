class Frame(object):
    def __init__(self, conn, buff):
        self.conn = conn
        self.request = buff.data
        self.problem = None
        self.action = None
        self.headers = {}
        try:
            problem_at = "action"
            i = buff.find("\r\n")
            self.action = buff.part(0,i).strip()
            buff.move(i+2)
            problem_at = "headers"
            i = buff.find("\r\n\r\n")
            self.headers = {}
            for line in buff.part(0,i).split('\r\n'):
                key, val = line.split(':',1)
                key, val = key.strip(), val.strip()
                problem_at = "headers: %s"%key
                if key == "recipient":
                    if "recipients" not in self.headers:
                        self.headers["recipients"] = []
                    self.headers["recipients"].append(val)
                else:
                    self.headers[key] = val
            buff.move(i+4)
            problem_at = "body"
            self.body = buff.data
        except:
            raise
            self.problem = 'parse error in %s'%problem_at

    def error(self, msg, cb=None, cbarg=()):
        if msg == self.problem:
            h = {"code":"1","reason":"error parsing frame"}
            msg += "\r\n---frame---\r\n"+self.request+"\r\n-----------"
        elif "id" not in self.headers:
            h = {"code":"2","reason":"no id in headers"}
            msg += "\r\n---frame---\r\n"+self.request+"\r\n-----------"
        else:
            h = {"code":"3","error":"","id":self.headers["id"]}
        self.respond("ERROR", h, msg, cb, cbarg)

    def received(self, cb=None, cbarg=()):
        if self.headers["response"] == "receipt":
            self.respond("RECEIPT", cb=cb, cbarg=cbarg)

    def respond(self, action, headers=None, body="", cb=None, cbarg=()):
        if not headers:
            headers = {"id":self.request_id}
        self.conn.write(action, headers, body, cb, cbarg)

class SendFrame(Frame):
    def success(self, succ, cb=None, cbarg=()):
        self.conn.callback("success",{"id":self.request_id,"recipients":succ},cb,cbarg)

    def failure(self, fail, cb=None, cbarg=()):
        self.conn.callback("failure",{"id":self.request_id,"recipients":fail},cb,cbarg)
