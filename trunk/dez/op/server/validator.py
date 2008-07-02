class OPValidator(object):
    def __init__(self):
        self.actions = {
            "CONNECT": ['id','connection_id'],
            "SEND": ['id','recipients'],
            "WELCOME": ['id','user_key'],
            "UNWELCOME": ['id','user_key'],
            "CALLBACK": ['id','function'],
        }

    def __call__(self, req):
        if req.problem:
            req.error(req.problem)
            return False
        if req.action not in self.actions:
            req.error("invalid action:%s"%req.action)
            return False
        for header in self.actions[req.action]:
            if header not in req.headers:
                req.error("'%s' header missing from '%s' action"%(header,req.action))
                return False
        req.request_id = req.headers["id"]
        return True