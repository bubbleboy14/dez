from dez.http.server import HTTPResponse, HTTPVariableResponse
from dez.http.cache import NaiveCache, INotifyCache
from dez import io
import os

class StaticHandler(object):
    def __init__(self, server_name):
        self.server_name = server_name
        try:
            self.cache = INotifyCache()
            #print "static cache: INotifyCache"
        except:
            self.cache = NaiveCache()
            #print "static cache: NaiveCache"

    def __call__(self, req, prefix, directory):
        path = os.path.join(directory, req.url[len(prefix):])
        if os.path.isdir(path):
            url = req.url
            if url.endswith('/'):
                url = url[:-1]
            response = HTTPResponse(req)
            response.headers['Server'] = self.server_name
            response.write('<b>%s</b><br><br>'%url)
            response.write("<a href=%s>..</a><br>"%os.path.split(url)[0])
            for child in os.listdir(path):
                response.write("<a href=%s/%s>%s</a><br>"%(url,child,child))
            return response.dispatch()
        self.cache.get(req, path, self.__write, self.__stream, self.__404)

    def __write(self, req, path):
        response = HTTPResponse(req)
        response.headers['Server'] = self.server_name
        response.headers['Content-type'] = self.cache.get_type(path)
        response.write(self.cache.get_content(path))
        response.dispatch()

    def __stream(self, req, path):
        response = HTTPVariableResponse(req)
        response.headers['Server'] = self.server_name
        response.headers['Content-type'] = self.cache.get_type(path)
        self.__write_file(response, open(path), path)

    def __404(self, req):
        response = HTTPResponse(req)
        response.headers['Server'] = self.server_name
        response.status = '404 Not Found'
        response.write("<b>404</b><br>Requested resource \"<i>%s</i>\" not found" % req.url)
        response.dispatch()

    def __write_file(self, response, openfile, path):
        data = openfile.read(io.BUFFER_SIZE)
        if data == "":
            return response.end()
        self.cache.add_content(path, data)
        response.write(data, self.__write_file, [response, openfile, path])