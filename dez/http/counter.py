class Counter(object):
    def __init__(self):
        self.ips = {}
        self.devices = {}
        self.rolls = 0
        self.requests = 0
        self.connections = 0
        self.total_requests = 0
        self.total_connections = 0

    def roll(self):
        self.rolls += 1

    def ip(self, ip):
        if ip not in self.ips:
            self.ips[ip] = 0
        self.ips[ip] += 1

    def device(self, useragent):
        if useragent not in self.devices:
            self.devices[useragent] = 0
        self.devices[useragent] += 1

    def inc(self, ctype, sock=None):
        ts = "total_%s"%(ctype,)
        setattr(self, ts, getattr(self, ts) + 1)
        setattr(self, ctype, getattr(self, ctype) + 1)
        if sock:
            self.ip(sock.getpeername()[0])

    def dec(self, ctype):
        setattr(self, ctype, getattr(self, ctype) - 1)

    def report(self):
        return {
            "ips": self.ips,
            "rolls": self.rolls,
            "devices": self.devices,
            "requests": self.requests,
            "connections": self.connections,
            "total_requests": self.total_requests,
            "total_connections": self.total_connections
        }