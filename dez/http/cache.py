import os, magic, mimetypes, time, gzip, zlib, psutil
from functools import cmp_to_key
from datetime import datetime
from dez.logging import default_get_logger
from dez.http.inotify import INotify
from dez import io
try: # py2 only (for py2 gzip)
    from StringIO import StringIO
except:
    pass
GZ3 = hasattr(gzip, "compress")
ENCZ = ["gzip", "deflate"]
try:
    import brotli
    ENCZ = ["br"] + ENCZ
except:
    pass

TEXTEXTS = ["html", "css", "js"]
extra_mimes = {
    "wasm": "application/wasm"
}
MEMPAD = 200000000 # bytes padding.....

class Compressor(object):
    def __call__(self, item, encodings):
        for enc in ENCZ:
            if enc in encodings:
                if enc not in item:
                    item[enc] = getattr(self, enc)(item['content'])
                return item[enc], { "Content-Encoding": enc }
        return item['content'], {}

    def br(self, txt):
        return brotli.compress(txt)

    def deflate(self, txt):
        return zlib.compress(txt)

    def gzip(self, txt):
        if GZ3:
            return gzip.compress(txt)
        out = StringIO()
        with gzip.GzipFile(fileobj=out, mode="w") as f:
            f.write(txt)
        return out.getvalue()

    def reset(self, item):
        for enc in ENCZ:
            if enc in item:
                del item[enc]

class Tosser(object):
    id = 0
    def __init__(self, cache, get_logger=default_get_logger, mempad=MEMPAD):
        Tosser.id += 1
        self.id = Tosser.id
        self.cache = cache
        self.mempad = mempad or MEMPAD # 0 = default
        self.sorter = cmp_to_key(self._sort)
        self.log = get_logger("Tosser(%s)"%(self.id,))
        self.log.info("initialized with mempad: %s"%(self.mempad,))

    def _sort(self, ap, bp): # earliest last seen
        a = self.cache[ap]['accessed']
        b = self.cache[bp]['accessed']
        if (a < b):
            return -1
        elif (a == b):
            return 0
        elif (a > b):
            return 1

    def __call__(self, path):
        required = self.cache[path]['size'] + self.mempad
        files = list(filter(lambda k : 'accessed' in self.cache[k], self.cache.keys()))
        files.sort(key=self.sorter)
        free = psutil.virtual_memory().available
        self.log.debug("memory: %s free; %s required"%(free, required))
        while required > free:
            if not files:
                return self.log.error("nothing left to pop!!!!!")
            tosser = files.pop(0)
            size = self.cache[tosser]['size']
            free += size
            self.log.info("tossing %s to free up %s"%(tosser, size))
            del self.cache[tosser]

class BasicCache(object):
    id = 0
    def __init__(self, streaming="auto", get_logger=default_get_logger, mempad=MEMPAD):
        BasicCache.id += 1
        self.id = BasicCache.id
        self.cache = {}
        self.mimetypes = {}
        self.streaming = streaming # True|False|"auto"
        self.compress = Compressor()
        self.tosser = Tosser(self.cache, get_logger, mempad)
        self.log = get_logger("%s(%s)"%(self.__class__.__name__, self.id))
        self.log.debug("__init__")

    def _mimetype(self, path):
        mimetype = self.mimetypes.get(path)
        if not mimetype:
            mimetype = mimetypes.guess_type(path)[0]
            if not mimetype and "." in path:
                mimetype = extra_mimes.get(path.split(".")[1])
            if not mimetype:
                mimetype = magic.from_file(path.strip("/"), True) or "application/octet-stream"
            self.mimetypes[path] = mimetype
        return mimetype

    def __updateContent(self, path):
        item = self.cache[path]
        f = open(path,'rb') # b for windowz ;)
        item['content'] = f.read()
        f.close()
        self.compress.reset(item)

    def __update(self, path, resize=True):
        self.log.debug("__update", path)
        item = self.cache[path]
        if resize:
            item['size'] = os.stat(path).st_size
        item['mtime'] = os.path.getmtime(path)
        if self._stream(path):
            item['content'] = bool(item['size'])
        else:
            self.__updateContent(path)

    def _stream(self, path):
        p = self.cache[path]
        stream = self.streaming
        if stream == "auto":
            fmax = io.BUFFER_SIZE * 5000
            stream = path.split(".").pop() not in TEXTEXTS and p['size'] > fmax
            stream and self.log.info("streaming huge file: %s @ %s > %s"%(path, p['size'], fmax))
        self.log.debug("_stream", path, p['size'], stream)
        return stream

    def get_type(self, path):
        return self.cache[path]['type']

    def get_content(self, path, encodings=""):
        path in self.cache or self.init_path(path)
        item = self.cache[path]
        item['accessed'] = datetime.now()
        return self.compress(item, encodings) # returns data"", headers{}

    def get_mtime(self, path, pretty=False):
        if path in self.cache and "mtime" in self.cache[path]:
            mt = self.cache[path]["mtime"]
        else:
            mt = os.path.getmtime(path)
        if pretty:
            return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mt))
        return mt

    def add_content(self, path, data):
        self.cache[path]['content'] += data

    def init_path(self, path):
        self._new_path(path)
        self.tosser(path)
        self.__update(path, False)

    def _empty(self, path):
        return not self.cache[path]['size']

    def _return(self, req, path, write_back, stream_back, err_back):
        if self._empty(path):
            err_back(req)
        else:
            (self._stream(path) and stream_back or write_back)(req, path)

    def get(self, req, path, write_back, stream_back, err_back):
        path = path.split("?")[0]
        if self._is_current(path):
            self.log.debug("get", path, "CURRENT!")
            self._return(req, path, write_back, stream_back, err_back)
        elif os.path.isfile(path):
            self.log.debug("get", path, "INITIALIZING FILE!")
            self.init_path(path)
            self._return(req, path, write_back, stream_back, err_back)
        else:
            self.log.debug("get", path, "404!")
            err_back(req)

    def _new_path(self, path):
        self.cache[path] = {
            'content': '',
            'type': self._mimetype(path),
            'size': os.stat(path).st_size
        }

class NaiveCache(BasicCache):
    def _is_current(self, path):
        return path in self.cache and self.cache[path]['mtime'] == os.path.getmtime(path)

class INotifyCache(BasicCache):
    def __init__(self, streaming="auto", get_logger=default_get_logger):
        BasicCache.__init__(self, streaming, get_logger)
        self.inotify = INotify(self.__update)

    def _is_current(self, path):
        return path in self.cache

    def _new_path(self, path):
        BasicCache._new_path(self, path)
        self.inotify.add_path(path)