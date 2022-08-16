from dez.http.client import HTTPClient

HC = None

def http_client():
	global HC
	if not HC:
		HC = HTTPClient()
	return HC

def do_dispatch():
	import event
	event.signal(2, event.abort)
	event.dispatch()

def fetch(host, path="/", port=80, secure=False, headers={}, cb=None, timeout=1, json=False, dispatch=False):
	http_client().fetch(host, path, port, secure, headers, cb, timeout, json)
	dispatch and do_dispatch()

def post(host, path="/", port=80, secure=False, headers={}, data=None, text=None, cb=None, timeout=1, json=False, dispatch=False):
	http_client().post(host, path, port, secure, headers, data, text, cb, timeout, json)
	dispatch and do_dispatch()