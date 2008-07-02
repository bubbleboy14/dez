class STOMPValidator(object):
    def __init__(self):
        self.actions = {
            "CONNECT": [],
            "SEND": ['destination'],
            "SUBSCRIBE": ['destination'],
            "UNSUBSCRIBE": [],
            "BEGIN": ['transaction'],
            "COMMIT": ['transaction'],
            "ABORT": ['transaction'],
            "ACK": ['message-id'],
            "DISCONNECT": [],
        }

    def _error(self, req):
        estring = "ACTION:"+req.action
        estring += "\r\nHEADERS:"+str(req.headers)
        return estring

    def __call__(self, req):
        if req.problem:
            req.error(req.problem,self._error(req))
            return False
        if req.action not in self.actions:
            req.error("invalid action:%s"%req.action,self._error(req))
            return False
        for header in self.actions[req.action]:
            if header not in req.headers:
                req.error("'%s' header missing from '%s' action"%(header,req.action),self._error(req))
                return False
        if req.action == "CONNECT" and "receipt" in req.headers:
            req.error("'receipt' header in CONNECT - not allowed",self._error(req))
            return False
        if req.action == "UNSUBSCRIBE" and "destination" not in req.headers and "id" not in req.headers:
            req.error("'destination' header and 'id' header not in UNSUBSCRIBE (you need at least one)",self._error(req))
            return False
        return True