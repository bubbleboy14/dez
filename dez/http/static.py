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

    def __respond(self, req, path=None, ctype=False, data=[], stream=False):
        response = (stream and HTTPVariableResponse or HTTPResponse)(req)
        response.headers['Server'] = self.server_name
        if ctype:
            response.headers['Content-type'] = self.cache.get_type(path)
        if not path:
            response.status = "404 Not Found"
        for d in data:
            response.write(d)
        if stream:
            self.__write_file(response, open(path), path)
        else:
            response.dispatch()

    def __call__(self, req, prefix, directory):
        path = os.path.join(directory, req.url[len(prefix):])
        if os.path.isdir(path):
            url = req.url
            if url.endswith('/'):
                url = url[:-1]
            return self.__respond(req, data=[
                '<b>%s</b><br><br>'%(url,),
                "<a href=%s>..</a><br>"%(os.path.split(url)[0],)
            ] + ["<a href=%s/%s>%s</a><br>"%(url,child,child) for child in os.listdir(path)])
        self.cache.get(req, path, self.__write, self.__stream, self.__404)

    def __write(self, req, path):
        self.__respond(req, path, True, [self.cache.get_content(path)])

    def __stream(self, req, path):
        self.__respond(req, path, True, stream=True)

    def __404(self, req):
        self.__respond(req, data=[
            "<b>404</b><br>Requested resource \"<i>%s</i>\" not found" % (req.url,)
        ])

    def __write_file(self, response, openfile, path):
        data = openfile.read(io.BUFFER_SIZE)
        if data == "":
            return response.end()
        self.cache.add_content(path, data)
        response.write(data, self.__write_file, [response, openfile, path])