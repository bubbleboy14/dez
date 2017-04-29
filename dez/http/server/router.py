import re
from dez.logging import default_get_logger

class Router(object):
    def __init__(self, default_cb, default_args=[], roll_cb=None, rollz={}, get_logger=default_get_logger):
        self.log = get_logger("Router")
        self.default_cb = default_cb
        self.default_args = default_args
        self.roll_cb = roll_cb
        self.rollz = rollz
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
        self.prefixes.sort(self.pref_order)

    def pref_order(self, b, a):
        return cmp(len(a[0]),len(b[0]))

    def _check(self, url, req=None):
        for flag, domain in self.rollz.items():
            if url.startswith(flag) and req:
                ref = req.headers.get("referer", "")
                self.log.access("roll check! url: %s. referer: %s"%(url, ref))
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
