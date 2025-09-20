import rel
from dez.logging import default_get_logger

BANNED_PRE = ["/", "~"]
ALLOWED = {
	"user-agent": ["facebookexternalhit"]
}
SKETCH_BITS = ["..", "/.", ".sh", ".vm", ".cfc", ".dll", ".aspx", ".alfa", ".action", "deadaed", "Smuggle:",
	"/aws", "/sdk", "/ajax", "/resolve", "/query", "/dns-query", "/live_env", "/global-protect", "/testing-put",
	"php", "boaform", "goform", "cgi", "GponForm", "elfinder", "ckeditor", "EmpireCMS", "utodiscover",
	"/dana-na/", "/laravel/", "/redmine/", "/webtools/", "/agent/", "/ALFA_DATA/", "/geoserver/", "Callmonitor",
	"/v1/", "/cf_scripts/", "/onvif/", "/seeyon/", "/stalker_portal/", "/remote/", "/service/", "//recordings/",
	"/owa/", "/totp/", "/vpnsvc/", "/pfblockerng/", "/ztp/", "/owncloud/", "/luci/", "/filemanager/",
	"/cms/", "/docker/", "/RDWeb/", "/kcfinder/", "/kubepi/", "/dup-installer/", "/pmd/", "/moodle/",
	"/private/", "/system/", "/zb_system/", "/cp/", "/_profiler/", "/__tests__/", "gsocket.io", "mstshash=",
	"/logincheck", "/MyCRL", "/Telerik", "/xmlrpc", "/wp-", "/FD87", ".html/", "/categories/Yud",
	"androxgh0st", "3.1.05160", "4.10.05111", "5.1.8.105", "system.listMethods", "doAuthentication.do", "TruffleHog",
	"0x01%5B%5D=legion", "0x%5B%5D=ridho", "0x%5B%5D=DTAB", "a=a", "debug=true", "debug=command", "EX=_tools",
	"username=admin&password=admin", "user=test&passwd=test", "action=getsoftware", "no-inspection-host=1"]

LIMIT = 200
INTERVAL = 2

def isallowed(txt, agroup):
	for abit in ALLOWED.get(agroup, []):
		if abit in txt:
			return True

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
		ipd = self.ip(ip)
		ipd["suss"] = True
		self.has_suss = True
		self.blacklist[ip] = ipd["message"] = reason
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

	def path(self, path, fspath=False, allow=None):
		if fspath:
			c1 = path[0]
			if c1 in BANNED_PRE:
				return True
		for sb in SKETCH_BITS:
			if sb in path:
				if allow and isallowed(path, allow):
					self.log.info("allowing: %s"%(path,))
				else:
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