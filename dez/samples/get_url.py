from dez.http.client import HTTPClient
import rel
    
def main(**kwargs):
    #url = "http://www.google.com:80/search?q=orbited"
    url = "http://%s:%s/"%(kwargs['domain'],kwargs['port'])
    c = HTTPClient()
    c.get_url(url, cb=req_cb, timeout=1)
    rel.signal(2, rel.abort)
    rel.dispatch()

def req_cb(response):
    print(response.status_line)
