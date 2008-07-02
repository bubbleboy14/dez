from dez.http.application import HTTPApplication

def simple_app(environ, start_response):
    print 'POST DATA:'
    print environ['wsgi.input'].read()
    return []
    
def main(**kwargs):
    httpd = HTTPApplication(kwargs['domain'], kwargs['port'])
    httpd.add_wsgi_rule("/", simple_app)
    httpd.start()
