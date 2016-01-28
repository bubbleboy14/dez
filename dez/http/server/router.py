import re

class Router(object):
    def __init__(self, default_cb, default_args=[]):
        self.default_cb = default_cb
        self.default_args = default_args
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

    def _check(self, url):
        for rx, cb, args in self.regexs:
            if rx.match(url):
                return cb, args
        for prefix, cb, args in self.prefixes:
            if url.startswith(prefix):
                return cb, args

    def _try_index(self, url):
        return self._check(url + "index.html")

    def __call__(self, url):
        match = self._check(url) or self._try_index(url)
        if match:
            return match[0], match[1]
        return self.default_cb, self.default_args
