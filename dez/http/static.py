from dez.http.server import HTTPResponse, HTTPVariableResponse
from dez.http.cache import NaiveCache, INotifyCache
from dez import io
import os, urllib, event

class StaticHandler(object):
    def __init__(self, server_name):
        self.server_name = server_name
        try:
            self.cache = INotifyCache()
            #print "static cache: INotifyCache"
        except:
            self.cache = NaiveCache()
            #print "static cache: NaiveCache"

    def __respond(self, req, path=None, ctype=False, headers={}, data=[], stream=False):
        if stream:
            response = HTTPVariableResponse(req)
        else:
            response = HTTPResponse(req, False)
        response.headers['Server'] = self.server_name
        if ctype:
            response.headers['Content-Type'] = self.cache.get_type(path)
        for header in headers:
            response.headers[header] = headers[header]
        if not path:
            response.status = "404 Not Found"
        for d in data:
            response.write(d)
        if stream:
            openfile = open(path)
            limit = os.stat(path).st_size
            if "range" in req.headers:
                rs, re = self.__range(req, response.headers, limit)
                rs and openfile.seek(rs)
                if re:
                    limit = re - rs
            self.__write_file(response, openfile, path, limit)
        else:
            response.dispatch()

    def __call__(self, req, prefix, directory):
        url = urllib.unquote(req.url)
        if "*" in prefix: # regex
            path = directory + url
        else:
            path = os.path.join(directory, url[len(prefix):])
        if os.path.isdir(path):
            if not self._try_index(req, path):
                if url.endswith('/'):
                    url = url[:-1]
                return self.__respond(req, data=[
                    '<b>%s</b><br><br>'%(url,),
                    "<a href=%s>..</a><br>"%(os.path.split(url)[0],)
                ] + ["<a href=%s>%s</a><br>"%(urllib.quote("%s/%s"%(url,
                    child)),child) for child in os.listdir(path)])
        else:
            self.cache.get(req, path, self.__write, self.__stream, self.__404)

    def _try_index(self, req, path):
        indexp = os.path.join(path, "index.html")
        if os.path.isfile(indexp):
            req.url += "index.html"
            self.cache.get(req, indexp, self.__write, self.__stream, self.__404)
            return True
        return False

    def __range(self, req, headers, size):
        rs, re = req.headers["range"][6:].split("-")
        headers["Content-Range"] = "bytes %s-%s/%s"%(rs, re or size, size)
        headers["Accept-Range"] = "bytes"
        return int(rs), re and int(re) or None

    def __write(self, req, path):
        data = self.cache.get_content(path)
        headers = {}
        if "range" in req.headers:
            rs, re = self.__range(req, headers, len(data))
            data = data[rs:re]
        self.__respond(req, path, True, headers, [data])

    def __stream(self, req, path):
        self.__respond(req, path, True, stream=True)

    def __404(self, req):
        self.__respond(req, data=[
            "<b>404</b><br>Requested resource \"<i>%s</i>\" not found" % (req.url,)
        ])

    def __write_file(self, response, openfile, path, limit):
        data = openfile.read(min(limit, io.BUFFER_SIZE))
        limit -= len(data)
        if data == "":
            return response.end()
        self.cache.add_content(path, data)
        event.timeout(0, response.write, data, self.__write_file, [response, openfile, path, limit])