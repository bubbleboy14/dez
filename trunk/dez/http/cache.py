import mimetypes, os
from dez.http.inotify import INotify

class BasicCache(object):
    def __init__(self):
        self.cache = {}

    def _mimetype(self, url):
        mimetype = mimetypes.guess_type(url)[0]
        if not mimetype:
            mimetype = "application/octet-stream"
        return mimetype

    def get_type(self, path):
        return self.cache[path]['type']

    def get_content(self, path):
        return self.cache[path]['content']

    def add_content(self, path, data):
        self.cache[path]['content'] += data

    def get(self, req, path, write_back, stream_back, err_back):
        if self._is_current(path):
            return write_back(req, path)
        if os.path.isfile(path):
            self._new_path(path, req.url)
            return stream_back(req, path)
        err_back(req)

class NaiveCache(BasicCache):
    def _is_current(self, path):
        return path in self.cache and self.cache[path]['mtime'] == os.path.getmtime(path)

    def _new_path(self, path, url):
        self.cache[path] = {'mtime':os.path.getmtime(path),'type':self._mimetype(url),'content':''}

class INotifyCache(BasicCache):
    def __init__(self):
        self.cache = {}
        self.inotify = INotify(self.__update)

    def __update(self, path):
        f = open(path,'r')
        self.cache[path]['content'] = f.read()
        f.close()

    def _is_current(self, path):
        return path in self.cache

    def _new_path(self, path, url):
        self.cache[path] = {'type':self._mimetype(url),'content':''}
        self.inotify.add_path(path)