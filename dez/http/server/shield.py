import rel
from dez.logging import default_get_logger

BANNED_PRE = ["/", "~"]
SKETCH_BITS = ["..", "/.", ".sh", ".vm", ".cfc", ".dll", ".aspx", ".alfa", ".action",
	"/aws", "/sdk", "/ajax", "/resolve", "/query", "/dns-query", "/live_env", "/global-protect",
	"php", "boaform", "goform", "cgi", "GponForm", "elfinder", "ckeditor", "EmpireCMS", "utodiscover",
	"/dana-na/", "/laravel/", "/redmine/", "/webtools/", "/agent/", "/ALFA_DATA/", "/geoserver/",
	"/v1/", "/cf_scripts/", "/onvif/", "/seeyon/", "/stalker_portal/", "/remote/", "/service/",
	"/owa/", "/totp/", "/vpnsvc/", "/pfblockerng/", "/ztp/", "/owncloud/", "/luci/", "/filemanager/",
	"/cms/", "/docker/", "/RDWeb/", "/kcfinder/", "/kubepi/", "/dup-installer/", "/pmd/",
	"/private/", "/system/", "/zb_system/", "/cp/", "/_profiler/", "/__tests__/",
	"/MyCRL", "/Telerik", "/xmlrpc", "/wp-", "/FD87", ".html/", "/categories/Yud",
	"androxgh0st", "3.1.05160", "system.listMethods",
	"debug=true", "username=admin&password=admin", "EX=_tools"]

LIMIT = 200
INTERVAL = 2

class Shield(object):
	def __init__(self, blacklist={}, get_logger=default_get_logger, on_suss=None, limit=LIMIT, interval=INTERVAL):
		self.log = get_logger("Shield")
		self.ips = {}
		self.limit = limit
		self.interval = interval
		self.blacklist = blacklist
		self.on_suss = on_suss
		self.checkers = set()
		self.has_suss = False
		rel.timeout(interval, self.check)
		self.log.info("initialized with %s blacklisted IPs"%(len(blacklist.keys()),))

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
		self.ips[ip]["suss"] = True
		self.blacklist[ip] = self.ips[ip]["message"] = reason
		self.log.warn("suss %s : %s"%(ip, reason))

	def unsuss(self, ip, reason="oops"):
		self.has_suss = True
		sig = "unsuss(%s)"%(ip,)
		if ip in self.ips:
			self.ips[ip]["suss"] = False
			self.ips[ip]["message"] += " - reverted because " + reason
			self.log.warn("%s unflagging IP: %s"%(sig, self.ips[ip]["message"]))
		if ip in self.blacklist:
			del self.blacklist[ip]
			self.log.warn("%s unblacklisting IP"%(sig,))

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
		for sb in SKETCH_BITS:
			if sb in path:
				return True
		return False

	def __call__(self, path, ip, fspath=False, count=True):
		ipdata = self.ip(ip)
		if ipdata["suss"]:
			self.log.warn("suss IP %s requested %s"%(ip, path))
			return True
		count and self.count(ip)
		self.path(path, fspath) and self.suss(ip, path)
		return ipdata["suss"]