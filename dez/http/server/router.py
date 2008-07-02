class Router(object):
    def __init__(self, default_cb, default_args=[]):
        self.default_cb = default_cb
        self.default_args = default_args
        self.prefixes = []

    def register_prefix(self, prefix, cb, args):
        self.prefixes.append((prefix, cb, args))
        self.prefixes.sort(self.pref_order)

    def pref_order(self, b, a):
        return cmp(len(a[0]),len(b[0]))

    def __call__(self, url):
        for prefix, cb, args in self.prefixes:
            if url.startswith(prefix):
                return cb, args
        return self.default_cb, self.default_args
