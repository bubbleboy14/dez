import mimetypes, os
from dez.logging import default_get_logger
from dez.http.inotify import INotify

class BasicCache(object):
    id = 0
    def __init__(self, streaming=False, get_logger=default_get_logger):
        BasicCache.id += 1
        self.id = BasicCache.id
        self.cache = {}
        self.streaming = streaming
        self.log = get_logger("%s(%s)"%(self.__class__.__name__, self.id))
        self.log.debug("__init__")

    def _mimetype(self, url):
        mimetype = mimetypes.guess_type(url)[0]
        if not mimetype:
            mimetype = "application/octet-stream"
        return mimetype

    def __update(self, path):
        self.log.debug("__update", path, self.streaming)
        if self.streaming:
            self.cache[path]['content'] = bool(os.stat(path).st_size)
            self.log.debug("Content Present:", self.cache[path]['content'])
        else:
            f = open(path,'r')
            self.cache[path]['content'] = f.read()
            f.close()
            self.log.debug("Content Length:", len(self.cache[path]['content']))

    def get_type(self, path):
        return self.cache[path]['type']

    def get_content(self, path):
        return self.cache[path]['content']

    def add_content(self, path, data):
        self.cache[path]['content'] += data

    def _empty(self, path):
        return not self.cache[path]['content']

    def _return(self, req, path, write_back, stream_back, err_back):
        if self._empty(path):
            err_back(req)
        else:
            (self.streaming and stream_back or write_back)(req, path)

    def get(self, req, path, write_back, stream_back, err_back):
        if self._is_current(path):
            self.log.debug("get", path, "CURRENT!")
            self._return(req, path, write_back, stream_back, err_back)
        elif os.path.isfile(path):
            self.log.debug("get", path, "CREATING FROM FILE!")
            self._new_path(path, req.url)
            self.__update(path)
            self._return(req, path, write_back, stream_back, err_back)
        else:
            self.log.debug("get", path, "404!")
            err_back(req)

class NaiveCache(BasicCache):
    def _is_current(self, path):
        return path in self.cache and self.cache[path]['mtime'] == os.path.getmtime(path)

    def _new_path(self, path, url):
        self.cache[path] = {'mtime':os.path.getmtime(path),'type':self._mimetype(url),'content':''}

class INotifyCache(BasicCache):
    def __init__(self, streaming=False):
        self.cache = {}
        self.streaming = streaming
        self.inotify = INotify(self.__update)

    def _is_current(self, path):
        return path in self.cache

    def _new_path(self, path, url):
        self.cache[path] = {'type':self._mimetype(url),'content':''}
        self.inotify.add_path(path)