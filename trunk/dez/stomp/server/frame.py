class STOMPFrame(object):
    def __init__(self, conn, buffer):
        self.conn = conn
        self.request = buffer.data
        self.action = None
        self.headers = {}
        self.body = None
        try:
            self.problem = "error parsing action"
            tbreak = buffer.find('\n')
            self.action = buffer.part(0,tbreak)
            buffer.move(tbreak+1)
            self.problem = "error parsing headers"
            hbreak = buffer.find('\n\n')
            if hbreak != -1:
                self.headers = {}
                for header in buffer.part(0,hbreak).split('\n'):
                    key, val = header.split(': ')
                    self.headers[key] = val
                buffer.move(hbreak+2)
            self.problem = "error parsing body"
            self.body = buffer.data
            self.problem = None
        except:
            pass

    def connected(self, s):
        self.respond("CONNECTED",{"session":str(s)})

    def error(self, problem, body=""):
        self.respond("ERROR",{"message":problem},body,close=True)

    def received(self, rid, cb=None, cbarg=[]):
        if "receipt" in self.headers:
            self.respond("RECEIPT",{"receipt-id":rid},"",cb,cbarg)

    def respond(self, action, headers={}, body="", cb=None, args=[], close=False):
        self.conn.write(action,headers,body,cb,args,close)

    def close(self):
        self.conn.close()

class STOMPSendFrame(STOMPFrame):
    def __parse_headers(self, recips):
        s = ""
        for recip in recips:
            s += "recipient:"+str(recip)+"\r\n"
        return s

    def success(self, succ):
        self.conn.message("success",self.__parse_headers(succ))

    def failure(self, fail):
        self.conn.message("failure",self.__parse_headers(fail))
