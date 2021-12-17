import os, magic, mimetypes, time, gzip, zlib
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

class BasicCache(object):
    id = 0
    def __init__(self, streaming="auto", get_logger=default_get_logger):
        BasicCache.id += 1
        self.id = BasicCache.id
        self.cache = {}
        self.mimetypes = {}
        self.streaming = streaming # True|False|"auto"
        self.compress = Compressor()
        self.log = get_logger("%s(%s)"%(self.__class__.__name__, self.id))
        self.log.debug("__init__")

    def _mimetype(self, url):
        mimetype = self.mimetypes.get(url)
        if not mimetype:
            mimetype = mimetypes.guess_type(url)[0]
            if not mimetype and "." in url:
                mimetype = extra_mimes.get(url.split(".")[1])
            if not mimetype:
                mimetype = magic.from_file(url.strip("/"), True) or "application/octet-stream"
            self.mimetypes[url] = mimetype
        return mimetype

    def __updateContent(self, path):
        item = self.cache[path]
        f = open(path,'rb') # b for windowz ;)
        item['content'] = f.read()
        f.close()
        self.compress.reset(item)

    def __update(self, path):
        self.log.debug("__update", path)
        item = self.cache[path]
        if self._stream(path):
            item['content'] = bool(item['size'])
        else:
            self.__updateContent(path)

    def _stream(self, path):
        p = self.cache[path]
        p['size'] = os.stat(path).st_size
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
        if path not in self.cache: # bypasses stream!
            self._new_path(path)
            self.__updateContent(path)
        return self.compress(self.cache[path], encodings) # returns data"", headers{}

    def get_mtime(self, path, pretty=False):
        if path in self.cache and "mtime" in self.cache[path]:
            mt = self.cache[path]["mtime"]
        else: # not in inotify!!
            mt = os.path.getmtime(path)
        if pretty:
            return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(mt))
        return mt

    def add_content(self, path, data):
        self.cache[path]['content'] += data

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
            self._new_path(path, req.url)
            self.__update(path)
            self._return(req, path, write_back, stream_back, err_back)
        else:
            self.log.debug("get", path, "404!")
            err_back(req)

class NaiveCache(BasicCache):
    def _is_current(self, path):
        return path in self.cache and self.cache[path]['mtime'] == os.path.getmtime(path)

    def _new_path(self, path, url=None):
        self.cache[path] = {'mtime':os.path.getmtime(path),'type':self._mimetype(url or path),'content':''}

class INotifyCache(BasicCache):
    def __init__(self, streaming="auto", get_logger=default_get_logger):
        BasicCache.__init__(self, streaming, get_logger)
        self.inotify = INotify(self.__update)

    def _is_current(self, path):
        return path in self.cache

    def _new_path(self, path, url=None):
        self.cache[path] = {'type':self._mimetype(url or path),'content':''}
        self.inotify.add_path(path)