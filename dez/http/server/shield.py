import event
from dez.logging import default_get_logger

BANNED_PRE = ["/", "~"]

LIMIT = 200
INTERVAL = 2

class Shield(object):
	def __init__(self, blacklist=set(), get_logger=default_get_logger, on_suss=None, limit=LIMIT, interval=INTERVAL):
		self.log = get_logger("Shield")
		self.ips = {}
		self.limit = limit
		self.interval = interval
		self.blacklist = blacklist
		self.on_suss = on_suss
		self.checkers = set()
		self.has_suss = False
		event.timeout(interval, self.check)
		self.log.info("initialized with %s blacklisted IPs"%(len(blacklist),))

	def ip(self, ip):
		if ip not in self.ips:
			self.log.info("first request: %s"%(ip,))
			self.ips[ip] = {
				"count": 0,
				"suss": False
			}
		return self.ips[ip]

	def suss(self, ip, reason="you know why"):
		self.has_suss = True
		self.blacklist.add(ip)
		self.ips[ip]["suss"] = True
		self.ips[ip]["message"] = reason
		self.log.info("suss %s : %s"%(ip, reason))

	def check(self):
		for ip in self.checkers:
			ipdata = self.ip(ip)
			rdiff = ipdata["count"] - ipdata["lastCount"]
			if rdiff > self.limit:
				self.suss(ip, "%s requests in %s seconds"%(rdiff, self.interval))
		self.checkers.clear()
		self.has_suss and self.on_suss and self.on_suss()
		self.has_suss = False
		return True

	def count(self, ip):
		ipdata = self.ip(ip)
		if ip not in self.checkers:
			ipdata["lastCount"] = ipdata["count"]
			self.checkers.add(ip)
		ipdata["count"] += 1

	def path(self, path, fspath=False):
		if fspath:
			c1 = path[0]
			if c1 in BANNED_PRE:
				return True
		return ".." in path

	def __call__(self, path, ip, fspath=False, count=True):
		ipdata = self.ip(ip)
		if ipdata["suss"]:
			return True
		count and self.count(ip)
		self.path(path, fspath) and self.suss(ip, path)
		return ipdata["suss"]