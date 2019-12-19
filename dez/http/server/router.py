import re, sys
from dez.logging import default_get_logger
from functools import cmp_to_key
if sys.version_info > (3, 0):
    def cmp(v1, v2):
        if (v1 < v2):
            return -1
        elif (v1 == v2):
            return 0
        elif (v1 > v2):
            return 1

class Router(object):
    def __init__(self, default_cb, default_args=[], roll_cb=None, rollz={}, get_logger=default_get_logger, whitelist=[]):
        self.log = get_logger("Router")
        self.default_cb = default_cb
        self.default_args = default_args
        self.roll_cb = roll_cb
        self.rollz = rollz
        self.whitelist = whitelist
        self.prefixes = []
        self.regexs = []

    def register_cb(self, signature, cb, args):
        if "*" in signature: # write better regex detection...
            self.register_regex(signature, cb, args)
        else:
            self.register_prefix(signature, cb, args)

    def register_regex(self, restr, cb, args):
        self.regexs.append((re.compile(restr), cb, args))

    def register_prefix(self, prefix, cb, args):
        self.prefixes.append((prefix, cb, args))
        self.prefixes.sort(key=cmp_to_key(self.pref_order))

    def pref_order(self, b, a):
        return cmp(len(a[0]),len(b[0]))

    def _check(self, url, req=None):
        if req and (self.whitelist or self.rollz):
            ip = req.real_ip
            ref = req.headers.get("referer", "")
            self.log.access("roll check!\nurl: %s\nreferer: %s\nip: %s"%(url, ref, ip))
            if self.whitelist and ip not in self.whitelist:
                return self.roll_cb, []
            for flag, domain in list(self.rollz.items()):
                if url.startswith(flag):
                    if not ref or domain not in ref:
                        return self.roll_cb, []
            self.log.access("passed!")
        for rx, cb, args in self.regexs:
            if rx.match(url):
                return cb, args
        for prefix, cb, args in self.prefixes:
            if url.startswith(prefix):
                return cb, args

    def _try_index(self, url):
        return self._check(url + "index.html")

    def __call__(self, req):
        url = req.url
        match = self._check(url, req) or self._try_index(url)
        if match:
            return match[0], match[1]
        return self.default_cb, self.default_args
